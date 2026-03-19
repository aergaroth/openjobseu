from datetime import datetime, timezone
from typing import Any
import logging
from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register
from app.adapters.ats.utils import (
    normalize_source_datetime,
    sanitize_location,
    sanitize_url,
    to_utc_datetime,
)
from app.utils.cleaning import clean_description

logger = logging.getLogger(__name__)

class GreenhouseAdapter(ATSAdapter):
    dorking_target = "boards.greenhouse.io"
    source_name = "greenhouse"
    active = True
    API_URL_TEMPLATE = (
        "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    )

    @staticmethod
    def _resolve_board_token(company: dict) -> str:
        token = str(company.get("ats_slug") or "").strip()
        if not token:
            raise ValueError("ats_slug cannot be empty for greenhouse adapter")
        return token

    @staticmethod
    def _fallback_company_name(board_token: str) -> str:
        return board_token.replace("-", " ").replace("_", " ").strip() or "unknown"

    def fetch(self, company: dict, updated_since: Any = None) -> list[dict]:
        board_token = self._resolve_board_token(company)
        api_url = self._build_jobs_url(board_token, include_content=True)

        resp = self.session.get(api_url, timeout=15)
        resp.raise_for_status()

        payload = self._parse_json(resp, board_token)

        jobs = self._extract_jobs_from_payload(payload, "fetch")

        jobs = self._filter_incremental_jobs(jobs, updated_since, ["updated_at", "pubDate"])

        # Inject board_token into each job for stateless normalize()
        for job in jobs:
            if isinstance(job, dict):
                job["_ats_board_token"] = board_token

        return jobs

    def normalize(self, raw_job: dict) -> dict | None:
        # Extract board_token from raw_job (injected by fetch)
        board_token = raw_job.get("_ats_board_token")
        if not board_token:
            raise ValueError("Missing _ats_board_token in raw_job. Ensure fetch() was called.")
        
        raw_id = raw_job.get("id")
        title = (raw_job.get("title") or "").strip()
        source_url = sanitize_url(raw_job.get("absolute_url"))

        location = None
        raw_location = raw_job.get("location")
        if isinstance(raw_location, dict):
            location = sanitize_location(raw_location.get("name"))
        elif isinstance(raw_location, str):
            location = sanitize_location(raw_location)

        updated_at = normalize_source_datetime(raw_job.get("updated_at"))
        pub_date = normalize_source_datetime(raw_job.get("pubDate"))
        first_seen_at = updated_at or pub_date or datetime.now(timezone.utc).isoformat()

        company_name = (
            (raw_job.get("company_name") or "").strip()
            or (raw_job.get("company") or "").strip()
            or self._fallback_company_name(board_token)
        )

        description = self.build_description(raw_job, [
            (["content", "description"], None)
        ])

        if not raw_id or not title or not source_url:
            return None

        cleaned_description = clean_description(description, source=self.source_name)
        
        is_remote_location = "remote" in (location or "").lower()
        is_remote = self.detect_remote(title, location, explicit_flag=is_remote_location)

        # Normalize remote_scope using base class method
        normalized_remote_scope = self.normalize_remote_scope(location)

        department = None
        departments = raw_job.get("departments")
        if isinstance(departments, list) and departments:
            dept = departments[0]
            if isinstance(dept, dict):
                department = dept.get("name")
        if department and not isinstance(department, str):
            department = str(department)

        pay_bounds = raw_job.get("pay_bounds")
        bound = pay_bounds[0] if isinstance(pay_bounds, list) and pay_bounds else None
        salary_info = self.extract_salary(bound)

        return {
            "job_id": f"greenhouse:{board_token}:{raw_id}",
            "source": f"greenhouse:{board_token}",
            "source_job_id": str(raw_id),
            "source_url": source_url,
            "title": title,
            "company_name": company_name,
            "description": cleaned_description.strip(),
            "remote_source_flag": is_remote,
            "remote_scope": normalized_remote_scope,
            "department": department or None,
            "status": "new",
            "first_seen_at": first_seen_at,
            **salary_info,
        }

    def probe_jobs(self, slug: str) -> dict[str, Any]:
        board_token = str(slug or "").strip()
        if not board_token:
            raise ValueError("slug cannot be empty for greenhouse probe")

        api_url = self._build_jobs_url(board_token, include_content=False)
        resp = self.session.get(api_url, timeout=15)
        resp.raise_for_status()

        payload = self._parse_json(resp, board_token, context="probe")

        jobs = self._extract_jobs_from_payload(payload, "probe")

        jobs_total = 0
        remote_hits = 0
        recent_job_at: datetime | None = None

        for job in jobs:
            if not isinstance(job, dict):
                continue

            jobs_total += 1
            job_updated_at = to_utc_datetime(job.get("updated_at"))
            if job_updated_at is None:
                job_updated_at = to_utc_datetime(job.get("pubDate"))

            if job_updated_at and (recent_job_at is None or job_updated_at > recent_job_at):
                recent_job_at = job_updated_at

            title = (job.get("title") or "").lower()
            location_value = ""
            raw_location = job.get("location")
            if isinstance(raw_location, dict):
                location_value = raw_location.get("name") or ""
            elif isinstance(raw_location, str):
                location_value = raw_location

            location = sanitize_location(location_value) or ""
            
            is_remote_location = "remote" in location.lower()
            if self.detect_remote(title, location, explicit_flag=is_remote_location, is_probe=True):
                remote_hits += 1

        return {
            "jobs_total": jobs_total,
            "recent_job_at": recent_job_at,
            "remote_hits": remote_hits,
        }

    @classmethod
    def _build_jobs_url(cls, board_token: str, include_content: bool) -> str:
        url = cls.API_URL_TEMPLATE.format(board_token=board_token)
        if include_content:
            return url
        return url.replace("?content=true", "")

    @staticmethod
    def _extract_jobs_from_payload(payload: Any, context: str) -> list[dict]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            jobs = payload.get("jobs", [])
            if not isinstance(jobs, list):
                raise ValueError(f"Greenhouse {context} payload does not contain a jobs list")
            return jobs
        raise ValueError(f"Greenhouse {context} API did not return a list or dict payload")

register(GreenhouseAdapter.source_name, GreenhouseAdapter)