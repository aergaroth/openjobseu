from datetime import datetime, timezone
import logging
from typing import Dict, Optional

from app.workers.normalization.common import (
    normalize_source_datetime,
    sanitize_location,
    sanitize_url,
)

from app.workers.normalization.cleaning import clean_description


logger = logging.getLogger("openjobseu.normalization.remoteok")


def normalize_remoteok_job(raw: Dict) -> Optional[Dict]:
    """
    Normalize a single RemoteOK job entry to OpenJobsEU canonical model.

    Notes:
    - RemoteOK is globally remote-first (not EU-only)
    - EU filtering is conservative and based only on explicit signals
    - apply_url may point to external ATS or company site
    """

    try:
        # Basic required fields
        job_id = raw.get("id")
        title = raw.get("position")
        company = raw.get("company")
        url = sanitize_url(raw.get("url") or raw.get("apply_url"))

        if not job_id or not title or not company or not url:
            logger.warning(
                "remoteok job skipped due to missing required fields",
                extra={"job_id": job_id},
            )
            return None

        # Posted date handling
        # RemoteOK provides both ISO date and epoch
        posted_at = normalize_source_datetime(raw.get("date"))
        if not posted_at:
            posted_at = normalize_source_datetime(raw.get("epoch"))
        if not posted_at:
            posted_at = datetime.now(timezone.utc).isoformat()

        # Location / scope
        location = (sanitize_location(raw.get("location")) or "").lower()

        # Conservative EU detection
        eu_markers = [
            "europe",
            "eu",
            "european union",
        ]

        if any(marker in location for marker in eu_markers):
            remote_scope = "EU-wide"
        else:
            # Not confidently EU → still remote, but marked explicitly
            remote_scope = "worldwide"


        raw_description = raw.get("description", "") or ""
        cleaned_description = clean_description(
            raw_description,
            source="remoteok",
        )

        normalized = {
            "job_id": f"remoteok:{job_id}",
            "source": "remoteok",
            "source_job_id": str(job_id),
            "source_url": url,
            "title": title.strip(),
            "company_name": company.strip(),
            "description": cleaned_description,
            "remote_source_flag": True,
            "remote_scope": remote_scope,
            "status": "new",
            "first_seen_at": posted_at,
        }

        logger.debug(
            "remoteok job normalized",
            extra={
                "job_id": normalized["job_id"],
                "remote_scope": remote_scope,
            },
        )

        return normalized

    except Exception as exc:
        logger.error(
            "remoteok normalization failed",
            extra={"raw_id": raw.get("id")},
            exc_info=exc,
        )
        return None
