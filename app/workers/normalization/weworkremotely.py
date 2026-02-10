from datetime import datetime, timezone
from typing import Dict, Optional
import logging

from app.workers.normalization.common import normalize_source_datetime, sanitize_url

logger = logging.getLogger("openjobseu.normalization.weworkremotely")


def normalize_weworkremotely_job(raw: Dict) -> Optional[Dict]:
    """
    Normalize a single WeWorkRemotely RSS entry into the OpenJobsEU canonical model.

    Assumptions:
    - All jobs are remote
    - Scope is EU-wide by project definition
    - No reliable posted date → fallback to now()
    - Company name heuristic preserved from previous implementation
    """

    try:
        raw_title = (raw.get("title") or "").strip()
        link = sanitize_url(raw.get("link"))
        source_job_id = raw.get("id") or link

        if not raw_title or not link or not source_job_id:
            logger.warning(
                "weworkremotely job skipped due to missing required fields",
                extra={"title": raw_title, "link": link},
            )
            return None

        # --- Company name heuristic (preserved behavior) ---
        company = raw.get("author") or "unknown"
        title = raw_title

        # Safe heuristic: "Company: Job Title"
        if company == "unknown" and ":" in raw_title:
            possible_company, possible_title = raw_title.split(":", 1)

            if 2 <= len(possible_company.strip()) <= 80:
                company = possible_company.strip()
                title = possible_title.strip()

        first_seen_at = (
            normalize_source_datetime(raw.get("published"))
            or normalize_source_datetime(raw.get("updated"))
            or normalize_source_datetime(raw.get("published_parsed"))
            or normalize_source_datetime(raw.get("updated_parsed"))
            or datetime.now(timezone.utc).isoformat()
        )

        normalized = {
            "job_id": f"weworkremotely:{source_job_id}",
            "source": "weworkremotely",
            "source_job_id": source_job_id,
            "source_url": link,
            "title": title,
            "company_name": company,
            "description": raw.get("summary", "") or "",
            "remote": True,
            "remote_scope": "EU-wide",
            "status": "new",
            "first_seen_at": first_seen_at,
        }

        logger.debug(
            "weworkremotely job normalized",
            extra={"job_id": normalized["job_id"]},
        )

        return normalized

    except Exception as exc:
        logger.error(
            "weworkremotely normalization failed",
            extra={"raw_id": raw.get("id")},
            exc_info=exc,
        )
        return None
