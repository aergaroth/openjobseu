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


logger = logging.getLogger(__name__)


class AshbyAdapter(ATSAdapter):
    dorking_target = "jobs.ashbyhq.com"
    source_name = "ashby"
    active = True

    API_URL_TEMPLATE = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"

    @staticmethod
    def _resolve_slug(company: dict) -> str:
        slug = str(company.get("ats_slug") or "").strip()
        if not slug:
            raise ValueError("ats_slug cannot be empty for ashby adapter")
        return slug

    def fetch(self, company: dict, updated_since: Any = None) -> list[dict]:
        slug = self._resolve_slug(company)
        api_url = self.API_URL_TEMPLATE.format(slug=slug)

        resp = self.session.get(api_url, timeout=15)
        resp.raise_for_status()

        data = self._parse_json(resp, slug)

        jobs = data.get("jobs", [])

        if not isinstance(jobs, list):
            raise ValueError("Ashby API did not return a jobs list")

        jobs = self._filter_incremental_jobs(jobs, updated_since, ["updatedAt", "publishedAt"])

        for job in jobs:
            if isinstance(job, dict):
                job["_ats_slug"] = slug

        return jobs

    def normalize(self, raw_job: dict) -> dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            raise ValueError("Missing _ats_slug in raw_job. Ensure fetch() was called.")

        raw_id = raw_job.get("id")
        title = (raw_job.get("title") or "").strip()

        source_url = raw_job.get("jobUrl")
        if not source_url:
            source_url = f"https://jobs.ashbyhq.com/{slug}/{raw_id}"
        source_url = sanitize_url(source_url)

        location = sanitize_location(raw_job.get("location"))

        # Collect secondary locations and combine with primary for scope classification
        secondary_locations = raw_job.get("secondaryLocations") or []
        secondary_location_strs = [
            sanitize_location(loc.get("location"))
            for loc in secondary_locations
            if isinstance(loc, dict) and loc.get("location")
        ]
        secondary_location_strs = [s for s in secondary_location_strs if s]

        updated_at = normalize_source_datetime(raw_job.get("updatedAt") or raw_job.get("publishedAt"))
        first_seen_at = updated_at or datetime.now(timezone.utc).isoformat()

        company_name = slug.replace("-", " ").replace("_", " ").strip().title()

        description = self.build_description(raw_job, [(["descriptionHtml", "descriptionPlain"], None)])

        if not raw_id or not title or not source_url:
            return None

        is_remote_location = "remote" in (location or "").lower()
        # workplaceType takes precedence over the isRemote boolean flag.
        # Ashby sometimes sets isRemote=true on hybrid/onsite roles — trust the
        # more specific workplaceType field when available.
        workplace_type = (raw_job.get("workplaceType") or "").strip().lower()
        is_non_remote_workplace = workplace_type in ("hybrid", "onsite", "on-site")
        explicit_remote = (not is_non_remote_workplace and raw_job.get("isRemote") is True) or is_remote_location
        is_remote = self.detect_remote(
            title,
            location,
            explicit_flag=explicit_remote,
        )

        all_locations = [loc for loc in [location] + secondary_location_strs if loc]
        combined_scope = "; ".join(all_locations) if all_locations else location
        # Inject workplace type signal so the remote classifier can detect
        # hybrid/onsite roles even when the description contains remote-sounding perks.
        if workplace_type == "hybrid":
            combined_scope = (combined_scope + "; hybrid") if combined_scope else "hybrid"
        elif is_non_remote_workplace:
            combined_scope = (combined_scope + "; on-site") if combined_scope else "on-site"
        normalized_remote_scope = self.normalize_remote_scope(combined_scope)

        department = raw_job.get("departmentName")
        if department and not isinstance(department, str):
            department = str(department)

        comp = raw_job.get("compensationTier") or raw_job.get("compensation")
        salary_info = self.extract_salary(comp)

        return {
            "job_id": f"ashby:{slug}:{raw_id}",
            "source": f"ashby:{slug}",
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
            raise ValueError("slug cannot be empty for ashby probe")

        api_url = self.API_URL_TEMPLATE.format(slug=ats_slug)

        resp = self.session.get(api_url, timeout=15)
        resp.raise_for_status()

        data = self._parse_json(resp, ats_slug, context="probe")

        jobs = data.get("jobs", [])

        if not isinstance(jobs, list):
            raise ValueError("Ashby probe API did not return a jobs list")

        jobs_total = 0
        remote_hits = 0
        recent_job_at: datetime | None = None

        for job in jobs:
            if not isinstance(job, dict):
                continue

            jobs_total += 1
            job_updated_at = to_utc_datetime(job.get("updatedAt") or job.get("publishedAt"))

            if job_updated_at and (recent_job_at is None or job_updated_at > recent_job_at):
                recent_job_at = job_updated_at

            title = (job.get("title") or "").lower()
            location = sanitize_location(job.get("location")) or ""

            is_remote_location = "remote" in location.lower()
            if self.detect_remote(
                title,
                location,
                explicit_flag=(job.get("isRemote") is True or is_remote_location),
                is_probe=True,
            ):
                remote_hits += 1

        return {
            "jobs_total": jobs_total,
            "recent_job_at": recent_job_at,
            "remote_hits": remote_hits,
        }


register(AshbyAdapter.source_name, AshbyAdapter)
