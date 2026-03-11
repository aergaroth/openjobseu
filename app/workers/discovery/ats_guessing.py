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
)

logger = logging.getLogger("openjobseu.discovery")

MAX_COMPANIES_PER_RUN = 50
QUALITY_MIN_JOBS = 5
QUALITY_MIN_REMOTE_HITS = 1
QUALITY_MAX_AGE_DAYS = 120
PROVIDERS_TO_PROBE = [
    "greenhouse",
    "lever",
    "workable",
]
MAX_SLUG_CANDIDATES = 6


def _normalize_company_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()
    if not normalized:
        return ""
    return normalized.split()[0]


def _generate_slug_candidates(name: str) -> list[str]:
    base = _normalize_company_name(name)
    if not base:
        return []

    candidates: list[str] = [base]
    suffixes = ["hq", "inc", "labs", "jobs", "app"]

    for suffix in suffixes:
        if len(candidates) >= MAX_SLUG_CANDIDATES:
            break
        candidates.append(f"{base}{suffix}")
        if len(candidates) >= MAX_SLUG_CANDIDATES:
            break
        candidates.append(f"{base}-{suffix}")
        if len(candidates) >= MAX_SLUG_CANDIDATES:
            break

    return candidates[:MAX_SLUG_CANDIDATES]


def _is_recent(recent_job_at: object) -> bool:
    if not isinstance(recent_job_at, datetime):
        return False
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
        companies = load_discovery_companies(conn, limit=MAX_COMPANIES_PER_RUN)

    for row in companies:
        metrics["companies_scanned"] += 1
        company_id = str(row["company_id"])
        company_name = row.get("brand_name") or row.get("legal_name")
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

                jobs_total = probe_result.get("jobs_total") or 0
                remote_hits = probe_result.get("remote_hits") or 0
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
                        careers_url=row["careers_url"],
                    )

                if inserted:
                    metrics["ats_inserted"] += 1
                else:
                    metrics.setdefault("ats_duplicates", 0)
                    metrics["ats_duplicates"] += 1

                found_ats = True
                break

    logger.info(
        "ats_guessing_summary",
        extra={
            "component": "discovery",
            "phase": "ats_guessing",
            **metrics,
        },
    )

    return metrics