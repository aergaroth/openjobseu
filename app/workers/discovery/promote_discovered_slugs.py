from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta

from app.workers.discovery.ats_probe import probe_ats
from storage.db_engine import get_engine
from storage.repositories.discovery_repository import (
    get_or_create_placeholder_company,
    insert_discovered_company_ats,
    get_pending_discovered_slugs,
    update_discovered_slug_status,
)

logger = logging.getLogger("openjobseu.discovery")

QUALITY_MIN_JOBS = 1
QUALITY_MAX_AGE_DAYS = 120


def _fallback_company_name(slug: str) -> str:
    return str(slug or "").replace("-", " ").replace("_", " ").strip().title()


def _resolve_company_name(probe_result: dict, slug: str) -> str:
    raw_name = probe_result.get("company_name") if isinstance(probe_result, dict) else None
    name = str(raw_name or "").strip()
    return name or _fallback_company_name(slug)


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


def run_promote_discovered_slugs() -> dict[str, int]:
    started = time.perf_counter()
    metrics = {
        "slugs_processed": 0,
        "slugs_promoted": 0,
        "promoted_ats_inserted": 0,
        "slugs_rejected": 0,
    }

    engine = get_engine()

    with engine.connect() as conn:
        pending = get_pending_discovered_slugs(conn)

    for row in pending:
        slug_id = row["id"]
        provider = row["provider"]
        slug = row["slug"]
        metrics["slugs_processed"] += 1

        try:
            # Teamtailor tokens cannot be inferred from discovered public URLs.
            # Candidates are tracked separately with status=needs_token.
            if provider == "teamtailor":
                with engine.begin() as conn:
                    update_discovered_slug_status(conn, slug_id, "needs_token")
                continue

            probe_result = probe_ats(provider, slug)
            if not probe_result:
                with engine.begin() as conn:
                    update_discovered_slug_status(conn, slug_id, "rejected")
                metrics["slugs_rejected"] += 1
                continue

            try:
                jobs_total = int(probe_result.get("jobs_total") or 0)
            except (ValueError, TypeError):
                jobs_total = 0

            recent_job_at = probe_result.get("recent_job_at")

            if jobs_total < QUALITY_MIN_JOBS or not _is_recent(recent_job_at):
                logger.info(
                    "promote_discovered_slug_quality_rejected",
                    extra={
                        "component": "discovery",
                        "phase": "promote_discovered",
                        "provider": provider,
                        "slug": slug,
                        "jobs_total": jobs_total,
                        "recent_job_at": recent_job_at,
                        "min_jobs_required": QUALITY_MIN_JOBS,
                    },
                )
                with engine.begin() as conn:
                    update_discovered_slug_status(conn, slug_id, "rejected")
                metrics["slugs_rejected"] += 1
                continue

            with engine.begin() as conn:
                company_name = _resolve_company_name(probe_result, slug)
                company_id = get_or_create_placeholder_company(conn, company_name)
                inserted = insert_discovered_company_ats(
                    conn,
                    company_id=company_id,
                    provider=provider,
                    ats_slug=slug,
                    careers_url=None,
                )
                update_discovered_slug_status(conn, slug_id, "promoted")

            metrics["slugs_promoted"] += 1
            if inserted:
                metrics["promoted_ats_inserted"] += 1

        except Exception as e:
            logger.error(
                f"error promoting discovered slug [{provider}/{slug}]: {e}",
                exc_info=True,
                extra={"provider": provider, "slug": slug, "component": "discovery"},
            )

    metrics["duration_ms"] = int((time.perf_counter() - started) * 1000)
    logger.info(
        "promote_discovered_slugs_done",
        extra={"component": "discovery", "phase": "promote_discovered", **metrics},
    )
    return metrics
