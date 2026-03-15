from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Iterable

from app.workers.discovery.ats_probe import probe_ats
from storage.db_engine import get_engine
from storage.repositories.discovery_repository import (
    insert_discovered_company_ats,
    load_discovery_companies,
    update_discovery_last_checked_at,
)

logger = logging.getLogger("openjobseu.discovery")

MAX_COMPANIES_PER_RUN = 5
QUALITY_MIN_JOBS = 1
QUALITY_MIN_REMOTE_HITS = 0
QUALITY_MAX_AGE_DAYS = 120
PROVIDERS_TO_PROBE = [
    "greenhouse",
    "lever",
    "workable",
    "ashby",
]
MAX_SLUG_CANDIDATES = 10


def _generate_slug_candidates(name: str) -> list[str]:
    name_lower = (name or "").lower()
    
    name_clean = re.sub(r"\b(inc|llc|ltd|gmbh|corp|co|limited|group)\b\.?", "", name_lower).strip()
    if not name_clean:
        name_clean = name_lower

    base_hyphen = re.sub(r"[^a-z0-9\s_]+", "", name_clean)
    base_hyphen = re.sub(r"[\s_]+", "-", base_hyphen).strip("-")
    
    base_flat = re.sub(r"[^a-z0-9]+", "", name_clean)
    
    bases = []
    if base_hyphen:
        bases.append(base_hyphen)
    if base_flat and base_flat != base_hyphen:
        bases.append(base_flat)

    if not bases:
        return []

    candidates: list[str] = []
    for base in bases:
        if base not in candidates:
            candidates.append(base)
            
    suffixes = ["hq", "inc", "labs", "jobs", "app", "careers"]

    for suffix in suffixes:
        for base in bases:
            if len(candidates) >= MAX_SLUG_CANDIDATES:
                break
            cand1 = f"{base}{suffix}"
            if cand1 not in candidates:
                candidates.append(cand1)
                
            if len(candidates) >= MAX_SLUG_CANDIDATES:
                break
            cand2 = f"{base}-{suffix}"
            if cand2 not in candidates:
                candidates.append(cand2)

    return candidates[:MAX_SLUG_CANDIDATES]


def _is_recent(recent_job_at: object) -> bool:
    if not recent_job_at:
        return True
    if isinstance(recent_job_at, str):
        try:
            recent_job_at = datetime.fromisoformat(recent_job_at.replace("Z", "+00:00"))
        except ValueError:
            pass

    if not isinstance(recent_job_at, datetime):
        return True
    if recent_job_at.tzinfo is None:
        recent_job_at = recent_job_at.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=QUALITY_MAX_AGE_DAYS)
    return recent_job_at >= cutoff


def run_ats_guessing() -> dict[str, int]:
    engine = get_engine()
    metrics = {
        "companies_scanned": 0,
        "slug_candidates_tested": 0,
        "ats_detected": 0,
        "ats_inserted": 0,
        "ats_skipped_quality": 0,
    }

    with engine.connect() as conn:
        companies = load_discovery_companies(conn, phase="ats_guessing", limit=MAX_COMPANIES_PER_RUN)

    total = len(companies)
    for idx, row in enumerate(companies, 1):
        metrics["companies_scanned"] += 1
        company_id = None

        try:
            if hasattr(row, "_mapping"):
                company_id = str(row._mapping["company_id"])
                company_name = row._mapping.get("brand_name") or row._mapping.get("legal_name")
                careers_url = row._mapping.get("careers_url")
            elif hasattr(row, "get"):
                company_id = str(row["company_id"])
                company_name = row.get("brand_name") or row.get("legal_name")
                careers_url = row.get("careers_url")
            else:
                company_id = str(getattr(row, "company_id", row[0] if isinstance(row, tuple) else ""))
                company_name = getattr(row, "brand_name", None) or getattr(row, "legal_name", None)
                careers_url = getattr(row, "careers_url", None)
        
            slug_candidates = _generate_slug_candidates(company_name)

            if not slug_candidates:
                continue

            found_ats = False

            for provider in PROVIDERS_TO_PROBE:
                if found_ats:
                    break

                for slug in slug_candidates:
                    metrics["slug_candidates_tested"] += 1
                    probe_result = probe_ats(provider, slug)
                    if not probe_result:
                        continue

                    metrics["ats_detected"] += 1

                    try:
                        jobs_total = int(probe_result.get("jobs_total") or 0)
                    except (ValueError, TypeError):
                        jobs_total = 0
                        
                    try:
                        remote_hits = int(probe_result.get("remote_hits") or 0)
                    except (ValueError, TypeError):
                        remote_hits = 0
                    recent_job_at = probe_result.get("recent_job_at")

                    if (
                        jobs_total < QUALITY_MIN_JOBS
                        or remote_hits < QUALITY_MIN_REMOTE_HITS
                        or not _is_recent(recent_job_at)
                    ):
                        metrics["ats_skipped_quality"] += 1
                        continue

                    with engine.begin() as conn:
                        inserted = insert_discovered_company_ats(
                            conn,
                            company_id=company_id,
                            provider=provider,
                            ats_slug=slug,
                            careers_url=careers_url,
                        )

                    if inserted:
                        metrics["ats_inserted"] += 1
                    else:
                        metrics.setdefault("ats_duplicates", 0)
                        metrics["ats_duplicates"] += 1

                    found_ats = True
                    break
        except Exception as e:
            logger.error(f"error processing company in ats_guessing [{company_id}]: {e}", exc_info=True, extra={
                "company_id": company_id,
                "component": "discovery"
            })
        finally:
            if company_id:
                with engine.begin() as conn:
                    update_discovery_last_checked_at(conn, company_id=company_id, phase="ats_guessing")
                    
        if total > 0 and (idx % max(1, total // 10) == 0 or idx == total):
            pct = int((idx / total) * 100)
            filled = int(20 * idx / total)
            bar = "█" * filled + "-" * (20 - filled)
            logger.info(f"ats_guessing progress: [{bar}] {pct}% ({idx}/{total})")

    logger.info(
        "ats_guessing_summary",
        extra={
            "component": "discovery",
            "phase": "ats_guessing",
            **metrics,
        },
    )

    return metrics