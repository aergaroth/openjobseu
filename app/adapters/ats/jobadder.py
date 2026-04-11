import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register
from app.adapters.ats.utils import (
    normalize_source_datetime,
    sanitize_location,
    sanitize_url,
    to_utc_datetime,
)

logger = logging.getLogger(__name__)


class JobAdderAdapter(ATSAdapter):
    dorking_target = "app.jobadder.com"
    source_name = "jobadder"
    active = True

    API_URL_TEMPLATE = "https://api.jobadder.com/v2/jobboards/{board_id}/ads"
    PAGE_LIMIT = 100

    def __init__(self):
        super().__init__()
        token = os.environ.get("JOBADDER_API_TOKEN", "")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    @staticmethod
    def _resolve_board_id(company: dict) -> str:
        board_id = str(company.get("ats_slug") or "").strip()
        if not board_id:
            raise ValueError("ats_slug cannot be empty for jobadder adapter")
        return board_id

    def fetch(self, company: dict, updated_since: Any = None) -> list[dict]:
        board_id = self._resolve_board_id(company)
        api_url = self.API_URL_TEMPLATE.format(board_id=board_id)

        jobs: list[dict] = []
        offset = 0

        while True:
            params: dict[str, Any] = {
                "fields": "description",
                "limit": self.PAGE_LIMIT,
                "offset": offset,
            }

            resp = self.session.get(api_url, params=params, timeout=15)
            resp.raise_for_status()

            data = self._parse_json(resp, board_id)

            page_jobs = data.get("items", [])
            if not isinstance(page_jobs, list):
                raise ValueError("JobAdder API did not return an items list")

            jobs.extend(page_jobs)

            total = data.get("total", 0)
            offset += len(page_jobs)

            if not page_jobs or offset >= total:
                break

        jobs = self._filter_incremental_jobs(jobs, updated_since, ["updatedAt", "postedAt"])

        for job in jobs:
            if isinstance(job, dict):
                job["_ats_slug"] = board_id

        return jobs

    def normalize(self, raw_job: dict) -> dict | None:
        board_id = raw_job.get("_ats_slug")
        if not board_id:
            raise ValueError("Missing _ats_slug in raw_job. Ensure fetch() was called.")

        raw_id = raw_job.get("adId")
        title = (raw_job.get("title") or "").strip()

        # URL: prefer applicationUri, fall back to constructed URL
        source_url = raw_job.get("applicationUri")
        if not source_url and raw_id:
            source_url = f"https://jobadder.com/jobs/{raw_id}"
        source_url = sanitize_url(source_url)

        if not raw_id or not title or not source_url:
            return None

        # Location: categories.location takes precedence over free-text locationText
        categories = raw_job.get("categories") or {}
        raw_location = categories.get("location") or raw_job.get("locationText") or ""
        location = sanitize_location(raw_location)

        updated_at = normalize_source_datetime(raw_job.get("updatedAt") or raw_job.get("postedAt"))
        first_seen_at = updated_at or datetime.now(timezone.utc).isoformat()

        advertiser = raw_job.get("advertiser") or {}
        company_name = advertiser.get("name") or (board_id.replace("-", " ").replace("_", " ").strip().title())

        # Build description: full description first, then summary as fallback section
        description = self.build_description(
            raw_job,
            [
                ("description", None),
                ("summary", "Summary"),
            ],
        )

        # Prepend bullet points when present
        bullet_points = raw_job.get("bulletPoints") or []
        if isinstance(bullet_points, list) and bullet_points:
            items = "".join(f"<li>{bp}</li>" for bp in bullet_points if bp)
            if items:
                prefix = f"<ul>{items}</ul>"
                description = prefix + ("\n\n" + description if description else "")

        # Remote detection: locationType is the explicit signal
        location_type = (categories.get("locationType") or "").lower()
        explicit_remote = location_type in ("remote", "work from home")
        is_remote = self.detect_remote(title, location, explicit_flag=explicit_remote)

        normalized_remote_scope = self.normalize_remote_scope(location)

        # Department: may be a dict or a plain string
        department = raw_job.get("department")
        if isinstance(department, dict):
            department = department.get("name") or department.get("label")
        if department and not isinstance(department, str):
            department = str(department)

        # Salary: map JobAdder `per` field to `period` key expected by extract_salary
        salary_raw = raw_job.get("salary")
        if isinstance(salary_raw, dict):
            salary_normalized: dict | None = {
                "min": salary_raw.get("min"),
                "max": salary_raw.get("max"),
                "currency": salary_raw.get("currency"),
                "period": salary_raw.get("per") or salary_raw.get("ratePer"),
            }
        else:
            salary_normalized = None
        salary_info = self.extract_salary(salary_normalized)

        return {
            "job_id": f"jobadder:{board_id}:{raw_id}",
            "source": f"jobadder:{board_id}",
            "source_job_id": str(raw_id),
            "source_url": source_url,
            "title": title,
            "company_name": company_name,
            "description": description.strip(),
            "remote_source_flag": is_remote,
            "remote_scope": normalized_remote_scope,
            "department": department or None,
            "status": "new",
            "first_seen_at": first_seen_at,
            **salary_info,
        }

    def probe_jobs(self, slug: str) -> dict[str, Any]:
        board_id = str(slug or "").strip()
        if not board_id:
            raise ValueError("slug cannot be empty for jobadder probe")

        api_url = self.API_URL_TEMPLATE.format(board_id=board_id)
        params: dict[str, Any] = {"limit": self.PAGE_LIMIT, "offset": 0}

        resp = self.session.get(api_url, params=params, timeout=15)
        resp.raise_for_status()

        data = self._parse_json(resp, board_id, context="probe")

        jobs = data.get("items", [])
        if not isinstance(jobs, list):
            raise ValueError("JobAdder probe API did not return an items list")

        jobs_total = 0
        remote_hits = 0
        recent_job_at: datetime | None = None

        for job in jobs:
            if not isinstance(job, dict):
                continue

            jobs_total += 1
            job_updated_at = to_utc_datetime(job.get("updatedAt") or job.get("postedAt"))

            if job_updated_at and (recent_job_at is None or job_updated_at > recent_job_at):
                recent_job_at = job_updated_at

            title = (job.get("title") or "").lower()
            categories = job.get("categories") or {}
            raw_location = categories.get("location") or job.get("locationText") or ""
            location = sanitize_location(raw_location) or ""

            location_type = (categories.get("locationType") or "").lower()
            explicit_remote = location_type in ("remote", "work from home")

            if self.detect_remote(title, location, explicit_flag=explicit_remote, is_probe=True):
                remote_hits += 1

        return {
            "jobs_total": jobs_total,
            "recent_job_at": recent_job_at,
            "remote_hits": remote_hits,
        }


register(JobAdderAdapter.source_name, JobAdderAdapter)
