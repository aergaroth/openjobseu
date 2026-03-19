import logging
from datetime import datetime, timezone
from typing import Any, Dict
import concurrent.futures

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

class SmartrecruitersAdapter(ATSAdapter):
    dorking_target = "jobs.smartrecruiters.com"
    source_name = "smartrecruiters"
    active = True
    
    API_URL_TEMPLATE = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    
    @staticmethod
    def _resolve_slug(company: dict) -> str:
        slug = str(company.get("ats_slug") or "").strip()
        if not slug:
            raise ValueError("ats_slug cannot be empty for smartrecruiters adapter")
        return slug

    def fetch(self, company: dict, updated_since: Any = None) -> list[dict]:
        slug = self._resolve_slug(company)
        api_url = self.API_URL_TEMPLATE.format(slug=slug)

        # SmartRecruiters uses pagination, limit=100 is usually enough for a daily delta fetch.
        resp = self.session.get(f"{api_url}?limit=100", timeout=15)
        resp.raise_for_status()

        data = self._parse_json(resp, slug)
        jobs = data.get("content", [])
        
        if not isinstance(jobs, list):
            raise ValueError("SmartRecruiters API did not return a content list")

        jobs = self._filter_incremental_jobs(jobs, updated_since, ["releasedDate"])

        def _fetch_detail(job: dict) -> dict:
            if not isinstance(job, dict):
                return job
            job_id = job.get("id")
            if not job_id:
                return job
                
            try:
                detail_url = f"{api_url}/{job_id}"
                detail_resp = self.session.get(detail_url, timeout=15)
                detail_resp.raise_for_status()

                detail_job = self._parse_json(detail_resp, slug, context="detail", extra_log_fields={"job_id": job_id})
                
                # Płynnie łączymy skróconą zawartość z pełnym opisem HTML z detail_job
                job.update(detail_job)
                job["_ats_slug"] = slug
                return job
            except Exception as e:
                logger.warning(
                    "SmartRecruiters: failed to fetch details for slug=%s, id=%s. Falling back to summary.",
                    slug, job_id, exc_info=True
                )
                job["_ats_slug"] = slug
                return job

        if not jobs:
            return []
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            full_jobs = list(executor.map(_fetch_detail, jobs))
            
        return full_jobs

    def normalize(self, raw_job: dict) -> dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            raise ValueError("Missing _ats_slug in raw_job. Ensure fetch() was called.")
        
        raw_id = raw_job.get("id")
        title = (raw_job.get("name") or "").strip()
        
        source_url = raw_job.get("applyUrl") or f"https://jobs.smartrecruiters.com/{slug}/{raw_id}"
        source_url = sanitize_url(source_url)

        location_dict = raw_job.get("location") or {}
        location_parts = [str(location_dict.get(k)) for k in ["city", "region", "country"] if location_dict.get(k)]
        location = sanitize_location(" - ".join(location_parts))

        updated_at = normalize_source_datetime(raw_job.get("releasedDate"))
        first_seen_at = updated_at or datetime.now(timezone.utc).isoformat()

        company_dict = raw_job.get("company") or {}
        company_name = company_dict.get("name") or slug.replace("-", " ").replace("_", " ").strip().title()

        # SmartRecruiters dzieli pełny opis na pomniejsze sekcje "jobAd"
        job_ad = raw_job.get("jobAd") or {}
        sections = job_ad.get("sections") or {}
        desc_parts = []
        for sec_key in ["companyDescription", "jobDescription", "qualifications", "additionalInformation"]:
            sec_data = sections.get(sec_key)
            if isinstance(sec_data, dict) and sec_data.get("text"):
                title_text = sec_data.get("title")
                text_content = sec_data.get("text")
                desc_parts.append(f"<h3>{title_text}</h3>\n{text_content}" if title_text else text_content)
                    
        description = "\n\n".join(desc_parts)

        if not raw_id or not title or not source_url:
            return None

        cleaned_description = clean_description(description, source=self.source_name)
        
        is_remote_location = "remote" in (location or "").lower()
        is_remote_flag = location_dict.get("remote") is True
        is_remote = self.detect_remote(title, location, explicit_flag=(is_remote_flag or is_remote_location))

        normalized_remote_scope = self.normalize_remote_scope(location)

        dept_dict = raw_job.get("department") or {}
        department = str(dept_dict.get("label")) if dept_dict.get("label") else None

        # SmartRecruiters rzadko zwraca widełki wprost po API, polegamy na parserze z opisu w silniku reguł
        salary_info = self.extract_salary(None) 

        return {
            "job_id": f"smartrecruiters:{slug}:{raw_id}",
            "source": f"smartrecruiters:{slug}",
            "source_job_id": str(raw_id),
            "source_url": source_url,
            "title": title,
            "company_name": company_name,
            "description": cleaned_description.strip(),
            "remote_source_flag": is_remote,
            "remote_scope": normalized_remote_scope,
            "department": department,
            "status": "new",
            "first_seen_at": first_seen_at,
            **salary_info,
        }

    def probe_jobs(self, slug: str) -> dict[str, Any]:
        # SmartRecruiters ma solidne API skrócone - do probe wystarczy pierwszy list endpoint bez dociągania
        jobs = self.fetch({"ats_slug": slug})
        return {"jobs_total": len(jobs), "remote_hits": 0, "recent_job_at": None} # uproszczony probe

register(SmartrecruitersAdapter.source_name, SmartrecruitersAdapter)