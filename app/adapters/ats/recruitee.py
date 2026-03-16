import logging
import httpx
from typing import Dict, List

from app.adapters.ats.base import ATSAdapter

logger = logging.getLogger(__name__)

class RecruiteeAdapter(ATSAdapter):
    def fetch(self, slug: str) -> List[Dict]:
        url = f"https://{slug}.recruitee.com/api/offers"
        try:
            resp = httpx.get(url, timeout=15.0, follow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            return data.get("offers", [])
        except httpx.HTTPError as e:
            logger.debug(f"Recruitee fetch failed for {slug}: {e}")
            return []

    def normalize(self, raw_job: Dict) -> Dict | None:
        job_id = str(raw_job.get("id"))
        title = raw_job.get("title", "")
        description = raw_job.get("description", "")
        location = raw_job.get("location", "")
        url = raw_job.get("careers_url", "")
        department = raw_job.get("department", "")
        
        remote = raw_job.get("remote", False)
        
        return {
            "source_job_id": job_id,
            "title": title,
            "company_name": raw_job.get("company_name", ""),
            "description": description,
            "remote_scope": location if location else ("Remote" if remote else ""),
            "remote_source_flag": remote,
            "source_url": url,
            "status": "new",
            "department": department,
        }

    def probe_jobs(self, slug: str) -> Dict | None:
        jobs = self.fetch(slug)
        if not jobs:
            return None
            
        return {
            "jobs_total": len(jobs),
            "remote_hits": sum(1 for j in jobs if j.get("remote") or "remote" in str(j.get("location", "")).lower()),
            "recent_job_at": jobs[0].get("created_at") if jobs else None,
        }