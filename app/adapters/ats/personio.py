import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register

logger = logging.getLogger(__name__)

class PersonioAdapter(ATSAdapter):
    source_name = "personio"

    def fetch(self, company: Dict, updated_since: Any = None) -> List[Dict]:
        slug = str(company.get("ats_slug") or "").strip()
        if not slug:
            logger.warning("ats_slug is missing for personio company")
            return []

        url = f"https://{slug}.jobs.personio.de/xml"
        # Let exceptions bubble up to the worker for centralized error handling.
        resp = self.session.get(url, timeout=15.0)
        resp.raise_for_status()
            
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:
            # Log the specific parsing error but re-raise to signal failure to the worker.
            logger.warning("Personio XML parse failed for slug: %s", slug, exc_info=True)
            raise ValueError(f"Personio XML parse failed for {slug}") from e
            
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
                "_ats_slug": slug,
            }
            jobs.append(job)
            
        return jobs

    def normalize(self, raw_job: Dict) -> Dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            logger.warning("Personio normalize missing _ats_slug", extra={"raw_job_id": raw_job.get("id")})
            return None

        job_id = str(raw_job.get("id"))
        if not job_id:
            return None

        title = raw_job.get("name", "")
        description = raw_job.get("description", "")
        location = raw_job.get("office", "")
        
        remote_source_flag = "remote" in str(location).lower() or "remote" in str(title).lower()
        
        company_name = slug.replace("-", " ").replace("_", " ").strip().title()
        
        return {
            "job_id": f"personio:{slug}:{job_id}",
            "source": f"personio:{slug}",
            "source_job_id": job_id,
            "title": title,
            "company_name": company_name,
            "description": description,
            "remote_scope": location,
            "remote_source_flag": remote_source_flag,
            "source_url": "",  # No URL in Personio XML feed
            "status": "new",
            "department": raw_job.get("department", ""),
        }

    def probe_jobs(self, slug: str) -> Dict | None:
        jobs = self.fetch(company={"ats_slug": slug})
        if not jobs:
            return None
            
        remote_hits = sum(1 for j in jobs if "remote" in str(j.get("office", "")).lower() or "remote" in str(j.get("name", "")).lower())
        
        recent_job = None
        if jobs:
            recent_job = max(jobs, key=lambda j: j.get("createdAt") or "")
        return {
            "jobs_total": len(jobs),
            "remote_hits": remote_hits,
            "recent_job_at": recent_job.get("createdAt") if recent_job else None,
        }

register(PersonioAdapter.source_name, PersonioAdapter)