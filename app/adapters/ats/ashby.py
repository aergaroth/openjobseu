from datetime import datetime, timezone
from typing import Any, Dict
import logging
from requests.exceptions import JSONDecodeError

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

class AshbyAdapter(ATSAdapter):
    source_name = "ashby"
    active = True
    
    API_URL_TEMPLATE = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    
    REMOTE_KEYWORDS_NORMALIZE = [
        "remote job",
        "home based",
        "work from home",
        "fully remote",
    ]
    REMOTE_KEYWORDS_PROBE = [
        "remote",
        "anywhere",
        "distributed",
        "work from home",
    ]

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

        try:
            data = resp.json()
        except JSONDecodeError as e:
            raw_text = resp.text[:500]
            logger.error(
                "Failed to decode JSON from Ashby ATS", 
                extra={
                    "ats_slug": slug,
                    "http_status": resp.status_code,
                    "response_text": raw_text
                }
            )
            raise ValueError(f"Ashby API returned non-JSON response for {slug}") from e

        jobs = data.get("jobs", [])
        
        if not isinstance(jobs, list):
            raise ValueError("Ashby API did not return a jobs list")

        jobs = self._filter_incremental_jobs(jobs, updated_since)

        for job in jobs:
            if isinstance(job, dict):
                job["_ats_slug"] = slug

        return jobs

    @staticmethod
    def _filter_incremental_jobs(jobs: list[dict], updated_since: Any) -> list[dict]:
        if updated_since in (None, ""):
            return jobs

        cutoff = to_utc_datetime(updated_since)
        if cutoff is None:
            return jobs

        filtered_jobs: list[dict] = []
        for job in jobs:
            if not isinstance(job, dict):
                filtered_jobs.append(job)
                continue

            source_updated_at = to_utc_datetime(job.get("updatedAt") or job.get("publishedAt"))

            if source_updated_at is None or source_updated_at >= cutoff:
                filtered_jobs.append(job)

        return filtered_jobs

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

        updated_at = normalize_source_datetime(raw_job.get("updatedAt") or raw_job.get("publishedAt"))
        first_seen_at = updated_at or datetime.now(timezone.utc).isoformat()

        company_name = slug.replace("-", " ").replace("_", " ").strip().title()

        description = raw_job.get("descriptionHtml") or raw_job.get("descriptionPlain") or ""
        if not isinstance(description, str):
            description = str(description)

        if not raw_id or not title or not source_url:
            return None

        cleaned_description = clean_description(description, source=self.source_name)
        full_text = f"{title} {location or ''}".lower()
        
        is_remote_explicit = raw_job.get("isRemote") is True
        is_remote = is_remote_explicit or any(kw in full_text for kw in self.REMOTE_KEYWORDS_NORMALIZE)

        normalized_remote_scope = self.normalize_remote_scope(location)

        department = raw_job.get("departmentName")
        if department and not isinstance(department, str):
            department = str(department)

        salary_min = None
        salary_max = None
        salary_currency = None
        salary_period = None
        salary_source = None

        comp = raw_job.get("compensationTier") or raw_job.get("compensation")
        if isinstance(comp, dict):
            try:
                s_min = comp.get("minAmount") if comp.get("minAmount") is not None else comp.get("min")
                s_max = comp.get("maxAmount") if comp.get("maxAmount") is not None else comp.get("max")
                
                if s_min is not None:
                    salary_min = int(float(s_min))
                if s_max is not None:
                    salary_max = int(float(s_max))
                    
                salary_currency = comp.get("currencyCode") or comp.get("currency")
                if isinstance(salary_currency, str):
                    salary_currency = salary_currency.upper()
                    
                interval = str(comp.get("interval") or comp.get("period") or "").lower()
                if "year" in interval:
                    salary_period = "yearly"
                elif "month" in interval:
                    salary_period = "monthly"
                elif "hour" in interval:
                    salary_period = "hourly"

                if salary_min or salary_max:
                    salary_source = "ats_api"
            except (ValueError, TypeError):
                pass

        return {
            "job_id": f"ashby:{slug}:{raw_id}",
            "source": f"ashby:{slug}",
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
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "salary_period": salary_period,
            "salary_source": salary_source,
        }

    def probe_jobs(self, slug: str) -> dict[str, Any]:
        ats_slug = str(slug or "").strip()
        if not ats_slug:
            raise ValueError("slug cannot be empty for ashby probe")

        api_url = self.API_URL_TEMPLATE.format(slug=ats_slug)
        
        resp = self.session.get(api_url, timeout=15)
        resp.raise_for_status()

        try:
            data = resp.json()
        except JSONDecodeError as e:
            raw_text = resp.text[:500]
            logger.error(
                "Failed to decode JSON from Ashby ATS probe", 
                extra={
                    "ats_slug": ats_slug,
                    "http_status": resp.status_code,
                    "response_text": raw_text
                }
            )
            raise ValueError(f"Ashby probe API returned non-JSON response for {ats_slug}") from e

        jobs = data.get("jobs", [])

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
            full_text = f"{title} {location}".lower()
            
            is_remote_explicit = job.get("isRemote") is True
            if is_remote_explicit or any(keyword in full_text for keyword in self.REMOTE_KEYWORDS_PROBE):
                remote_hits += 1

        return {
            "jobs_total": jobs_total,
            "recent_job_at": recent_job_at,
            "remote_hits": remote_hits,
        }

register(AshbyAdapter.source_name, AshbyAdapter)