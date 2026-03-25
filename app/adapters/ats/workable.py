import logging
from datetime import datetime, timezone
from typing import Any
import concurrent.futures

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register
from app.adapters.ats.utils import (
    normalize_source_datetime,
    sanitize_location,
    sanitize_url,
    to_utc_datetime,
)

logger = logging.getLogger(__name__)


class WorkableAdapter(ATSAdapter):
    dorking_target = "apply.workable.com"
    source_name = "workable"
    active = True

    API_URL_TEMPLATE = "https://apply.workable.com/api/v3/accounts/{slug}/jobs"

    @staticmethod
    def _resolve_slug(company: dict) -> str:
        slug = str(company.get("ats_slug") or "").strip()
        if not slug:
            raise ValueError("ats_slug cannot be empty for workable adapter")
        return slug

    def fetch(self, company: dict, updated_since: Any = None) -> list[dict]:
        slug = self._resolve_slug(company)
        api_url = self.API_URL_TEMPLATE.format(slug=slug)

        payload = {
            "query": "",
            "location": [],
            "department": [],
            "worktype": [],
            "remote": [],
        }

        resp = self.session.post(api_url, json=payload, timeout=15)
        resp.raise_for_status()

        data = self._parse_json(resp, slug)

        jobs = data.get("results", [])

        if not isinstance(jobs, list):
            raise ValueError("Workable API did not return a results list")

        jobs = self._filter_incremental_jobs(jobs, updated_since, ["published"])

        def _fetch_detail(job: dict) -> dict:
            if not isinstance(job, dict):
                return job
            shortcode = job.get("shortcode")
            if not shortcode:
                return job

            try:
                detail_url = f"{api_url}/{shortcode}"
                detail_resp = self.session.get(detail_url, timeout=15)
                detail_resp.raise_for_status()

                detail_job = self._parse_json(
                    detail_resp,
                    slug,
                    context="detail",
                    extra_log_fields={"shortcode": shortcode},
                )

                detail_job["_ats_slug"] = slug
                return detail_job
            except Exception:
                logger.warning(
                    "Workable: failed to fetch job details for slug=%s, shortcode=%s. Falling back to summary.",
                    slug,
                    shortcode,
                    exc_info=True,
                )
                job["_ats_slug"] = slug
                return job

        if not jobs:
            return []

        # Współbieżnie odpytujemy API dla paczki ofert używając maksymalnie 3 wątków
        # na jedną firmę, aby nie obudzić w systemie Workable limitu Rate Limit (HTTP 429)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            full_jobs = list(executor.map(_fetch_detail, jobs))

        return full_jobs

    def normalize(self, raw_job: dict) -> dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            raise ValueError("Missing _ats_slug in raw_job. Ensure fetch() was called.")

        raw_id = raw_job.get("shortcode")
        title = (raw_job.get("title") or "").strip()

        source_url = raw_job.get("url")
        if not source_url:
            source_url = f"https://apply.workable.com/{slug}/j/{raw_id}/"
        source_url = sanitize_url(source_url)

        location_dict = raw_job.get("location") or {}
        location_parts = []
        if location_dict.get("city"):
            location_parts.append(location_dict.get("city"))
        if location_dict.get("region"):
            location_parts.append(location_dict.get("region"))
        if location_dict.get("country"):
            location_parts.append(location_dict.get("country"))

        location = sanitize_location(", ".join(location_parts))

        updated_at = normalize_source_datetime(raw_job.get("published"))
        first_seen_at = updated_at or datetime.now(timezone.utc).isoformat()

        company_name = slug.replace("-", " ").replace("_", " ").strip().title()

        description = self.build_description(
            raw_job,
            [
                ("description", None),
                ("requirements", "Requirements"),
                ("benefits", "Benefits"),
            ],
        )

        if not raw_id or not title or not source_url:
            return None

        is_remote_location = "remote" in (location or "").lower()
        is_remote = self.detect_remote(
            title,
            location,
            explicit_flag=(raw_job.get("remote") is True or is_remote_location),
        )

        normalized_remote_scope = self.normalize_remote_scope(location)

        department = None
        dept_raw = raw_job.get("department")
        if isinstance(dept_raw, list) and dept_raw:
            department = str(dept_raw[0])
        elif isinstance(dept_raw, str):
            department = dept_raw

        salary_data = raw_job.get("salary")
        salary_info = self.extract_salary(salary_data)

        return {
            "job_id": f"workable:{slug}:{raw_id}",
            "source": f"workable:{slug}",
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
        ats_slug = str(slug or "").strip()
        if not ats_slug:
            raise ValueError("slug cannot be empty for workable probe")

        api_url = self.API_URL_TEMPLATE.format(slug=ats_slug)
        payload = {
            "query": "",
            "location": [],
            "department": [],
            "worktype": [],
            "remote": [],
        }

        resp = self.session.post(api_url, json=payload, timeout=15)
        resp.raise_for_status()

        data = self._parse_json(resp, ats_slug, context="probe")

        jobs = data.get("results", [])

        if not isinstance(jobs, list):
            raise ValueError("Workable probe API did not return a results list")

        jobs_total = 0
        remote_hits = 0
        recent_job_at: datetime | None = None

        for job in jobs:
            if not isinstance(job, dict):
                continue

            jobs_total += 1
            job_updated_at = to_utc_datetime(job.get("published"))

            if job_updated_at and (recent_job_at is None or job_updated_at > recent_job_at):
                recent_job_at = job_updated_at

            title = (job.get("title") or "").lower()
            location_dict = job.get("location") or {}
            location_value = f"{location_dict.get('city', '')} {location_dict.get('country', '')}"

            location = sanitize_location(location_value) or ""

            is_remote_location = "remote" in location.lower()
            if self.detect_remote(
                title,
                location,
                explicit_flag=(job.get("remote") is True or is_remote_location),
                is_probe=True,
            ):
                remote_hits += 1

        return {
            "jobs_total": jobs_total,
            "recent_job_at": recent_job_at,
            "remote_hits": remote_hits,
        }


register(WorkableAdapter.source_name, WorkableAdapter)
