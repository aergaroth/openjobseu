import logging
import httpx
import xml.etree.ElementTree as ET
from typing import Dict, List

from app.adapters.ats.base import ATSAdapter

logger = logging.getLogger(__name__)

class PersonioAdapter(ATSAdapter):
    def fetch(self, slug: str) -> List[Dict]:
        url = f"https://{slug}.jobs.personio.de/xml"
        try:
            resp = httpx.get(url, timeout=15.0)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.debug(f"Personio fetch failed for {slug}: {e}")
            return []
            
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            logger.debug(f"Personio XML parse failed for {slug}")
            return []
            
        jobs = []
        for position in root.findall("position"):
            # Opisy w Personio są często podzielone na sekcje (np. wymagania, obowiązki)
            desc_texts = []
            for desc in position.findall(".//jobDescription/value"):
                if desc.text:
                    desc_texts.append(desc.text.strip())
                    
            job = {
                "id": position.findtext("id"),
                "name": position.findtext("name"),
                "description": "\n\n".join(desc_texts),
                "office": position.findtext("office"),
                "department": position.findtext("department"),
                "createdAt": position.findtext("createdAt"),
            }
            jobs.append(job)
            
        return jobs

    def normalize(self, raw_job: Dict) -> Dict | None:
        job_id = str(raw_job.get("id"))
        title = raw_job.get("name", "")
        description = raw_job.get("description", "")
        location = raw_job.get("office", "")
        
        remote_source_flag = "remote" in location.lower() or "remote" in title.lower()
        
        return {
            "source_job_id": job_id,
            "title": title,
            "company_name": "", 
            "description": description,
            "remote_scope": location,
            "remote_source_flag": remote_source_flag,
            "source_url": "",
            "status": "new",
            "department": raw_job.get("department", ""),
        }

    def probe_jobs(self, slug: str) -> Dict | None:
        jobs = self.fetch(slug)
        if not jobs:
            return None
            
        remote_hits = sum(1 for j in jobs if "remote" in str(j.get("office", "")).lower() or "remote" in str(j.get("name", "")).lower())
        return {
            "jobs_total": len(jobs),
            "remote_hits": remote_hits,
            "recent_job_at": jobs[0].get("createdAt") if jobs else None,
        }