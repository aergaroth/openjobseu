import logging
from typing import Any, Dict, List

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register
from app.adapters.ats.utils import to_utc_datetime
from app.utils.cleaning import clean_description

logger = logging.getLogger(__name__)

class RecruiteeAdapter(ATSAdapter):
    dorking_target = "recruitee.com"
    source_name = "recruitee"

    def fetch(self, company: Dict, updated_since: Any = None) -> List[Dict]:
        slug = str(company.get("ats_slug") or "").strip()
        if not slug:
            logger.warning("ats_slug is missing for recruitee company")
            return []

        url = f"https://{slug}.recruitee.com/api/offers"
        # Let exceptions bubble up to the worker for centralized error handling.
        # The base adapter uses `requests`, so we use `self.session`.
        
        # Explicitly ask Recruitee not to keep-alive the connection to prevent 
        # [SSL: UNEXPECTED_EOF_WHILE_READING] warnings in logs caused by abrupt server closures.
        resp = self.session.get(url, timeout=15.0, headers={"Connection": "close"})
        resp.raise_for_status()

        data = self._parse_json(resp, slug)

        offers = data.get("offers")
        if offers is None:
            offers = []
            
        if not isinstance(offers, list):
            raise ValueError(f"Recruitee API did not return an offers list for {slug}")

        for offer in offers:
            if isinstance(offer, dict):
                offer["_ats_slug"] = slug
        return self._filter_incremental_jobs(offers, updated_since, ["created_at"])

    def normalize(self, raw_job: Dict) -> Dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            logger.warning("Recruitee normalize missing _ats_slug", extra={"raw_job_id": raw_job.get("id")})
            return None

        raw_id = raw_job.get("id")
        if not raw_id:
            return None
        job_id = str(raw_id)

        title = raw_job.get("title", "")
        location = raw_job.get("location", "")
        url = raw_job.get("careers_url", "")
        department = raw_job.get("department", "")
        remote = raw_job.get("remote", False)
        
        description = self.build_description(raw_job, [
            ("description", None),
            ("requirements", "Requirements"),
        ])
        cleaned_description = clean_description(description, source=self.source_name)
        
        is_remote_location = "remote" in (location or "").lower()
        is_remote = self.detect_remote(title, location, explicit_flag=(remote is True or is_remote_location))
        
        normalized_remote_scope = self.normalize_remote_scope(location if location else ("Remote" if remote else ""))

        company_name = raw_job.get("company_name", "")
        if not company_name:
            company_name = slug.replace("-", " ").replace("_", " ").strip().title()

        return {
            "job_id": f"recruitee:{slug}:{job_id}",
            "source": f"recruitee:{slug}",
            "source_job_id": job_id,
            "title": title,
            "company_name": company_name,
            "description": cleaned_description.strip(),
            "remote_scope": normalized_remote_scope,
            "remote_source_flag": is_remote,
            "source_url": url,
            "status": "new",
            "department": department,
        }

    def probe_jobs(self, slug: str) -> Dict | None:
        jobs = self.fetch(company={"ats_slug": slug})
        if not jobs:
            return None
            
        return {
            "jobs_total": len(jobs),
            "remote_hits": sum(
                1 for j in jobs 
                if self.detect_remote(
                    j.get("title"), 
                    j.get("location"), 
                    explicit_flag=(bool(j.get("remote")) or "remote" in (j.get("location") or "").lower()), 
                    is_probe=True
                )
            ),
            "recent_job_at": jobs[0].get("created_at") if jobs else None,
        }

register(RecruiteeAdapter.source_name, RecruiteeAdapter)