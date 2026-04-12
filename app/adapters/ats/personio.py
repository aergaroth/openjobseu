import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterator, List, cast

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register

logger = logging.getLogger(__name__)


class PersonioAdapter(ATSAdapter):
    dorking_target = "jobs.personio.com"
    source_name = "personio"
    active = True

    def fetch(self, company: Dict, updated_since: Any = None) -> List[Dict]:
        slug = str(company.get("ats_slug") or "").strip()
        if not slug:
            logger.warning("ats_slug is missing for personio company")
            return []

        url = f"https://{slug}.jobs.personio.de/xml"
        # Let exceptions bubble up to the worker for centralized error handling.
        resp = self.session.get(url, timeout=15.0, stream=True)
        resp.raise_for_status()

        jobs = []
        bytes_read = 0
        parser = ET.XMLPullParser(["end"])

        try:
            for chunk in resp.iter_content(chunk_size=8192):
                bytes_read += len(chunk)
                if bytes_read > 10 * 1024 * 1024:  # Sztywny limit wielkości do 10MB dla kanału XML
                    raise ValueError(f"Personio XML feed is too large (>10MB) for slug: {slug}")

                # Na bieżąco karmimy parser paczkami z sieci
                parser.feed(chunk)

                events = cast(Iterator[tuple[str, ET.Element]], parser.read_events())
                for _, elem in events:
                    if elem.tag == "position":
                        desc_texts = []
                        for desc_node in elem.findall(".//jobDescription"):
                            name = desc_node.findtext("name")
                            value = desc_node.findtext("value")
                            if value and value.strip():
                                if name and name.strip():
                                    desc_texts.append(f"<h3>{name.strip()}</h3>\n{value.strip()}")
                                else:
                                    desc_texts.append(value.strip())

                        job = {
                            "id": elem.findtext("id"),
                            "name": elem.findtext("name"),
                            "description": "\n\n".join(desc_texts),
                            "office": elem.findtext("office"),
                            "department": elem.findtext("department"),
                            "createdAt": elem.findtext("createdAt"),
                            "_ats_slug": slug,
                        }
                        jobs.append(job)

                        # Błyskawiczne zwolnienie pamięci po przeprocesowaniu całego węzła
                        elem.clear()

            parser.close()
        except ET.ParseError as e:
            logger.warning("Personio XML parse failed for slug: %s", slug, exc_info=True)
            raise ValueError(f"Personio XML parse failed for {slug}") from e

        return self._filter_incremental_jobs(jobs, updated_since, ["createdAt"])

    def normalize(self, raw_job: Dict) -> Dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            logger.warning(
                "Personio normalize missing _ats_slug",
                extra={"raw_job_id": raw_job.get("id")},
            )
            return None

        job_id = raw_job.get("id")
        if not job_id:
            return None
        job_id = str(job_id)

        title = raw_job.get("name", "")
        description = raw_job.get("description", "")
        location = raw_job.get("office", "")

        normalized_remote_scope = self.normalize_remote_scope(location)

        is_remote_office = "remote" in location.lower()
        remote_source_flag = self.detect_remote(title, location, explicit_flag=is_remote_office)

        company_name = slug.replace("-", " ").replace("_", " ").strip().title()

        return {
            "job_id": f"personio:{slug}:{job_id}",
            "source": f"personio:{slug}",
            "source_job_id": job_id,
            "title": title,
            "company_name": company_name,
            "description": description.strip(),
            "remote_scope": normalized_remote_scope,
            "remote_source_flag": remote_source_flag,
            "source_url": "",  # No URL in Personio XML feed
            "status": "new",
            "department": raw_job.get("department", ""),
        }

    def probe_jobs(self, slug: str) -> Dict[str, Any]:
        jobs = self.fetch(company={"ats_slug": slug})
        if not jobs:
            return {
                "jobs_total": 0,
                "remote_hits": 0,
                "recent_job_at": None,
            }

        remote_hits = sum(
            1
            for j in jobs
            if self.detect_remote(
                j.get("name"),
                j.get("office"),
                explicit_flag="remote" in (j.get("office") or "").lower(),
                is_probe=True,
            )
        )

        recent_job = None
        if jobs:
            recent_job = max(jobs, key=lambda j: j.get("createdAt") or "")
        return {
            "jobs_total": len(jobs),
            "remote_hits": remote_hits,
            "recent_job_at": recent_job.get("createdAt") if recent_job else None,
        }


register(PersonioAdapter.source_name, PersonioAdapter)
