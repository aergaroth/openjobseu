'''
put in:
app/workers/normalization/
'''

from datetime import datetime, timezone
import logging
from typing import Dict, Optional

from app.workers.normalization.common import (
    normalize_source_datetime,
    sanitize_location,
    sanitize_url,
)


logger = logging.getLogger("openjobseu.normalization.greenhouse")


def _fallback_company_name(board_token: str) -> str:
    return board_token.replace("-", " ").replace("_", " ").strip() or "unknown"


def normalize_greenhouse_job(raw_job: Dict, board_token: str) -> Optional[Dict]:
    try:
        raw_id = raw_job.get("id")
        title = (raw_job.get("title") or "").strip()
        source_url = sanitize_url(raw_job.get("absolute_url"))

        location = None
        raw_location = raw_job.get("location")
        if isinstance(raw_location, dict):
            location = sanitize_location(raw_location.get("name"))
        elif isinstance(raw_location, str):
            location = sanitize_location(raw_location)

        updated_at = normalize_source_datetime(raw_job.get("updated_at"))
        pub_date = normalize_source_datetime(raw_job.get("pubDate"))
        first_seen_at = updated_at or pub_date or datetime.now(timezone.utc).isoformat()

        company_name = (
            (raw_job.get("company_name") or "").strip()
            or (raw_job.get("company") or "").strip()
            or _fallback_company_name(board_token)
        )

        description = raw_job.get("content") or raw_job.get("description") or ""
        if not isinstance(description, str):
            description = str(description)

        if not raw_id or not title or not source_url:
            logger.warning(
                "greenhouse job skipped due to missing required fields",
                extra={"raw_id": raw_id, "board_token": board_token},
            )
            return None

        full_text = f"{title} {description} {location or ''}".lower()

        REMOTE_KEYWORDS = [
            "remote",
            "home based",
            "work from home",
            "fully remote",
        ]

        is_remote = any(kw in full_text for kw in REMOTE_KEYWORDS)

        normalized = {
            "job_id": f"greenhouse:{board_token}:{raw_id}",
            "source": f"greenhouse:{board_token}",
            "source_job_id": str(raw_id),
            "source_url": source_url,
            "title": title,
            "company_name": company_name,
            "description": description.strip(),
            "remote_source_flag": is_remote,
            "remote_scope": location,
            "status": "new",
            "first_seen_at": first_seen_at,
        }
        logger.debug(
            "greenhouse job normalized",
            extra={
                "job_id": normalized["job_id"],
                "source": normalized["source"],
            },
        )
        return normalized

    except Exception as exc:
        logger.error(
            "greenhouse normalization failed",
            extra={"raw_id": raw_job.get("id"), "board_token": board_token},
            exc_info=exc,
        )
        return None
