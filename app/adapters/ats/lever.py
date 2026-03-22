from datetime import datetime, timezone
from typing import Any, Dict
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


class LeverAdapter(ATSAdapter):
    dorking_target = "jobs.lever.co"
    source_name = "lever"
    active = True
    API_URL_TEMPLATE = "https://api.lever.co/v0/postings/{slug}?mode=json"

    @staticmethod
    def _resolve_slug(company: dict) -> str:
        slug = str(company.get("ats_slug") or "").strip()
        if not slug:
            raise ValueError("ats_slug cannot be empty for lever adapter")
        return slug

    def fetch(self, company: Dict, updated_since: Any = None):
        slug = self._resolve_slug(company)
        api_url = self.API_URL_TEMPLATE.format(slug=slug)

        resp = self.session.get(api_url, timeout=15)
        resp.raise_for_status()

        jobs = self._parse_json(resp, slug)

        if not isinstance(jobs, list):
            raise ValueError("Lever API did not return a list payload")

        jobs = self._filter_incremental_jobs(jobs, updated_since, ["createdAt"])

        for job in jobs:
            if isinstance(job, dict):
                job["_ats_slug"] = slug

        return jobs

    def normalize(self, raw_job: Dict) -> Dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            raise ValueError("Missing _ats_slug in raw_job. Ensure fetch() was called.")

        raw_id = raw_job.get("id")
        title = (raw_job.get("text") or "").strip()
        source_url = sanitize_url(raw_job.get("hostedUrl"))

        location = None
        categories = raw_job.get("categories") or {}
        raw_location = categories.get("location")
        if isinstance(raw_location, str):
            location = sanitize_location(raw_location)

        workplace_type = raw_job.get("workplaceType") or ""

        updated_at = normalize_source_datetime(raw_job.get("createdAt"))
        first_seen_at = updated_at or datetime.now(timezone.utc).isoformat()

        company_name = slug.replace("-", " ").replace("_", " ").strip().title()

        # Assemble full description from Lever's fragmented payload
        desc_parts = []
        main_desc = self.build_description(raw_job, [(["description", "descriptionPlain"], None)])
        if main_desc:
            desc_parts.append(main_desc)

        for lst in raw_job.get("lists") or []:
            if isinstance(lst, dict):
                heading = lst.get("text")
                content = lst.get("content")
                if content:
                    desc_parts.append(f"<h3>{heading}</h3>\n{content}" if heading else str(content))

        add_desc = self.build_description(raw_job, [(["additional", "additionalPlain"], None)])
        if add_desc:
            desc_parts.append(add_desc)

        description = "\n\n".join(desc_parts)

        if not raw_id or not title or not source_url:
            return None

        cleaned_description = clean_description(description, source=self.source_name)

        is_remote_location = "remote" in (location or "").lower()
        is_remote = self.detect_remote(
            title,
            location,
            explicit_flag=(workplace_type.lower() == "remote" or is_remote_location),
            extra_text=workplace_type,
        )

        normalized_remote_scope = self.normalize_remote_scope(location)

        department = categories.get("department") or categories.get("team")
        if department and not isinstance(department, str):
            department = str(department)

        salary_range = raw_job.get("salaryRange") or raw_job.get("salary")
        salary_info = self.extract_salary(salary_range)

        return {
            "job_id": f"lever:{slug}:{raw_id}",
            "source": f"lever:{slug}",
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

    def probe_jobs(self, slug: str) -> Dict[str, Any]:
        ats_slug = str(slug or "").strip()
        if not ats_slug:
            raise ValueError("slug cannot be empty for lever probe")

        api_url = self.API_URL_TEMPLATE.format(slug=ats_slug)
        resp = self.session.get(api_url, timeout=15)
        resp.raise_for_status()

        jobs = self._parse_json(resp, ats_slug, context="probe")

        if not isinstance(jobs, list):
            raise ValueError("Lever API did not return a list payload")

        jobs_total = 0
        remote_hits = 0
        recent_job_at: datetime | None = None

        for job in jobs:
            if not isinstance(job, dict):
                continue

            jobs_total += 1
            job_updated_at = to_utc_datetime(job.get("createdAt"))

            if job_updated_at and (recent_job_at is None or job_updated_at > recent_job_at):
                recent_job_at = job_updated_at

            title = (job.get("text") or "").lower()
            categories = job.get("categories") or {}
            location_value = categories.get("location") or ""
            workplace_type = (job.get("workplaceType") or "").lower()

            location = sanitize_location(location_value) or ""

            is_remote_location = "remote" in location.lower()
            if self.detect_remote(
                title,
                location,
                explicit_flag=(workplace_type == "remote" or is_remote_location),
                extra_text=workplace_type,
                is_probe=True,
            ):
                remote_hits += 1

        return {
            "jobs_total": jobs_total,
            "recent_job_at": recent_job_at,
            "remote_hits": remote_hits,
        }


register(LeverAdapter.source_name, LeverAdapter)
