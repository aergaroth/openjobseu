import logging
from datetime import datetime, timezone
from typing import Any, Dict
import concurrent.futures
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

class WorkableAdapter(ATSAdapter):
    dorking_target = "apply.workable.com"
    source_name = "workable"
    active = True
    
    API_URL_TEMPLATE = "https://apply.workable.com/api/v3/accounts/{slug}/jobs"
    
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
            "remote": []
        }
        
        resp = self.session.post(api_url, json=payload, timeout=15)
        resp.raise_for_status()

        try:
            data = resp.json()
        except JSONDecodeError as e:
            raw_text = resp.text[:500]
            logger.error(
                "Failed to decode JSON from Workable ATS", 
                extra={
                    "ats_slug": slug,
                    "http_status": resp.status_code,
                    "response_text": raw_text
                }
            )
            raise ValueError(f"Workable API returned non-JSON response for {slug}") from e

        jobs = data.get("results", [])
        
        if not isinstance(jobs, list):
            raise ValueError("Workable API did not return a results list")

        jobs = self._filter_incremental_jobs(jobs, updated_since)

        def _fetch_detail(job: dict) -> dict:
            if not isinstance(job, dict):
                return job
            shortcode = job.get("shortcode")
            if not shortcode:
                return job
                
            try:
                detail_url = f"{api_url}/{shortcode}"
                detail_resp = self.session.get(detail_url, timeout=10)
                detail_resp.raise_for_status()

                try:
                    detail_job = detail_resp.json()
                except JSONDecodeError as e:
                    raw_text = detail_resp.text[:500]
                    logger.error(
                        "Failed to decode JSON from Workable ATS detail", 
                        extra={
                            "ats_slug": slug,
                            "shortcode": shortcode,
                            "http_status": detail_resp.status_code,
                            "response_text": raw_text
                        }
                    )
                    raise ValueError(f"Workable detail API returned non-JSON response for {slug}/{shortcode}") from e

                detail_job["_ats_slug"] = slug
                return detail_job
            except Exception as e:
                logger.warning(
                    "Workable: failed to fetch job details for slug=%s, shortcode=%s. Falling back to summary.",
                    slug, shortcode, exc_info=True
                )
                job["_ats_slug"] = slug
                return job

        if not jobs:
            return []
            
        # Współbieżnie odpytujemy API dla paczki ofert używając maksymalnie 5 wątków 
        # na jedną firmę, aby nie obudzić w systemie Workable limitu Rate Limit (HTTP 429)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            full_jobs = list(executor.map(_fetch_detail, jobs))
            
        return full_jobs

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

            source_updated_at = to_utc_datetime(job.get("published"))

            if source_updated_at is None or source_updated_at >= cutoff:
                filtered_jobs.append(job)

        return filtered_jobs

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

        desc_parts = []
        if raw_job.get("description"):
            desc_parts.append(str(raw_job["description"]))
        if raw_job.get("requirements"):
            desc_parts.append("<h3>Requirements</h3>\n" + str(raw_job["requirements"]))
        if raw_job.get("benefits"):
            desc_parts.append("<h3>Benefits</h3>\n" + str(raw_job["benefits"]))

        description = "\n\n".join(desc_parts)

        if not raw_id or not title or not source_url:
            return None

        cleaned_description = clean_description(description, source=self.source_name)
        full_text = f"{title} {location or ''}".lower()
        
        is_remote_explicit = raw_job.get("remote") is True
        is_remote = is_remote_explicit or any(kw in full_text for kw in self.REMOTE_KEYWORDS_NORMALIZE)

        normalized_remote_scope = self.normalize_remote_scope(location)

        department = None
        dept_raw = raw_job.get("department")
        if isinstance(dept_raw, list) and dept_raw:
            department = str(dept_raw[0])
        elif isinstance(dept_raw, str):
            department = dept_raw

        salary_min = None
        salary_max = None
        salary_currency = None
        salary_period = None
        salary_source = None

        salary_data = raw_job.get("salary")
        if isinstance(salary_data, dict):
            try:
                s_min = salary_data.get("min")
                s_max = salary_data.get("max")
                
                if s_min is not None:
                    salary_min = int(float(s_min))
                if s_max is not None:
                    salary_max = int(float(s_max))
                    
                salary_currency = salary_data.get("currency")
                if isinstance(salary_currency, str):
                    salary_currency = salary_currency.upper()
                    
                unit = str(salary_data.get("type") or salary_data.get("unit") or "").lower()
                if "year" in unit:
                    salary_period = "yearly"
                elif "month" in unit:
                    salary_period = "monthly"
                elif "hour" in unit:
                    salary_period = "hourly"

                if salary_min or salary_max:
                    salary_source = "ats_api"
            except (ValueError, TypeError):
                pass

        return {
            "job_id": f"workable:{slug}:{raw_id}",
            "source": f"workable:{slug}",
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
            raise ValueError("slug cannot be empty for workable probe")

        api_url = self.API_URL_TEMPLATE.format(slug=ats_slug)
        payload = {
            "query": "",
            "location": [],
            "department": [],
            "worktype": [],
            "remote": []
        }
        
        resp = self.session.post(api_url, json=payload, timeout=15)
        resp.raise_for_status()

        try:
            data = resp.json()
        except JSONDecodeError as e:
            raw_text = resp.text[:500]
            logger.error(
                "Failed to decode JSON from Workable ATS probe", 
                extra={
                    "ats_slug": ats_slug,
                    "http_status": resp.status_code,
                    "response_text": raw_text
                }
            )
            raise ValueError(f"Workable probe API returned non-JSON response for {ats_slug}") from e

        jobs = data.get("results", [])

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
            full_text = f"{title} {location}".lower()
            
            is_remote_explicit = job.get("remote") is True
            if is_remote_explicit or any(keyword in full_text for keyword in self.REMOTE_KEYWORDS_PROBE):
                remote_hits += 1

        return {
            "jobs_total": jobs_total,
            "recent_job_at": recent_job_at,
            "remote_hits": remote_hits,
        }

register(WorkableAdapter.source_name, WorkableAdapter)