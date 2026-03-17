import logging
from typing import Any, Dict, List

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register

logger = logging.getLogger(__name__)

class RecruiteeAdapter(ATSAdapter):
    source_name = "recruitee"

    def fetch(self, company: Dict, updated_since: Any = None) -> List[Dict]:
        slug = str(company.get("ats_slug") or "").strip()
        if not slug:
            logger.warning("ats_slug is missing for recruitee company")
            return []

        url = f"https://{slug}.recruitee.com/api/offers"
        # Let exceptions bubble up to the worker for centralized error handling.
        # The base adapter uses `requests`, so we use `self.session`.
        resp = self.session.get(url, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        offers = data.get("offers", [])
        for offer in offers:
            if isinstance(offer, dict):
                offer["_ats_slug"] = slug
        return offers

    def normalize(self, raw_job: Dict) -> Dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            logger.warning("Recruitee normalize missing _ats_slug", extra={"raw_job_id": raw_job.get("id")})
            return None

        job_id = str(raw_job.get("id"))
        if not job_id:
            return None

        title = raw_job.get("title", "")
        description = raw_job.get("description", "")
        location = raw_job.get("location", "")
        url = raw_job.get("careers_url", "")
        department = raw_job.get("department", "")
        remote = raw_job.get("remote", False)
        
        company_name = raw_job.get("company_name", "")
        if not company_name:
            company_name = slug.replace("-", " ").replace("_", " ").strip().title()

        return {
            "job_id": f"recruitee:{slug}:{job_id}",
            "source": f"recruitee:{slug}",
            "source_job_id": job_id,
            "title": title,
            "company_name": company_name,
            "description": description,
            "remote_scope": location if location else ("Remote" if remote else ""),
            "remote_source_flag": remote,
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
            "remote_hits": sum(1 for j in jobs if j.get("remote") or "remote" in str(j.get("location", "")).lower()),
            "recent_job_at": jobs[0].get("created_at") if jobs else None,
        }

register(RecruiteeAdapter.source_name, RecruiteeAdapter)