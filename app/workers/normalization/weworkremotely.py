from datetime import datetime, timezone
from typing import Dict, Optional
import hashlib
import re
from urllib.parse import urlsplit

from app.workers.normalization.common import normalize_source_datetime, sanitize_url

def _looks_like_url_fragment(value: str) -> bool:
    v = (value or "").strip().lower()
    return (
        v.startswith("http")
        or v.startswith("www.")
        or "://" in v
        or "/" in v
        or v.endswith(".com")
        or v.endswith(".org")
        or v.endswith(".io")
    )


def _is_url_like(value: str | None) -> bool:
    v = (value or "").strip().lower()
    return v.startswith("http://") or v.startswith("https://") or "://" in v


def _safe_wwr_source_job_id(raw_id: str | None, link: str) -> str:
    """
    Keep source ids stable and URL-free for downstream consumers.
    """
    rid = (raw_id or "").strip()
    if rid and not _is_url_like(rid):
        return rid

    path = urlsplit(link).path.strip("/")
    slug = path.split("/")[-1] if path else ""
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", slug).strip("-")
    if slug:
        return slug

    return hashlib.sha1(link.encode("utf-8")).hexdigest()[:16]


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
        source_job_id = _safe_wwr_source_job_id(raw.get("id"), link or "")

        if not raw_title or not link or not source_job_id:
            return None

        # --- Company name heuristic (preserved behavior) ---
        company = raw.get("author") or "unknown"
        title = raw_title

        # Safe heuristic: "Company: Job Title"
        if company == "unknown" and ":" in raw_title:
            possible_company, possible_title = raw_title.split(":", 1)
            possible_company = possible_company.strip()
            possible_title = possible_title.strip()

            if (
                2 <= len(possible_company) <= 80
                and not _looks_like_url_fragment(possible_company)
            ):
                company = possible_company
                title = possible_title

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
            "remote_source_flag": True,
            "remote_scope": "EU-wide",
            "status": "new",
            "first_seen_at": first_seen_at,
        }

        return normalized

    except Exception:
        return None
