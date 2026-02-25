import logging
from time import perf_counter

from app.workers.compliance_resolver import resolve_compliance
from storage.db import get_engine
from storage.sqlite import (
    backfill_missing_compliance_classes,
    count_jobs_missing_compliance,
    get_jobs_for_compliance_resolution,
    update_job_compliance_resolution,
)

logger = logging.getLogger("openjobseu.compliance")


def run_compliance_resolution(limit: int = 500, *, only_missing: bool = False) -> dict:
    """
    Resolve compliance status and score for persisted jobs.

    This runs after ingestion and before post-ingestion workers.
    """
    started = perf_counter()
    checked = 0
    updated = 0

    try:
        jobs = get_jobs_for_compliance_resolution(
            limit=limit,
            only_missing=only_missing,
        )
        checked = len(jobs)

        db_engine = get_engine()
        batch_updated = 0
        with db_engine.begin() as conn:
            for job in jobs:
                result = resolve_compliance(
                    job.get("remote_class"),
                    job.get("geo_class"),
                )
                update_job_compliance_resolution(
                    job_id=job["job_id"],
                    compliance_status=result["compliance_status"],
                    compliance_score=int(result["compliance_score"]),
                    conn=conn,
                )
                batch_updated += 1
        updated = batch_updated
    except Exception:
        logger.exception("compliance resolution step failed")

    duration_ms = int((perf_counter() - started) * 1000)
    summary = {
        "checked": checked,
        "updated": updated,
        "duration_ms": duration_ms,
        "only_missing": only_missing,
    }

    logger.info(
        "compliance_resolution_summary",
        extra={
            "component": "compliance",
            "phase": "compliance_resolution_summary",
            "checked": checked,
            "updated": updated,
            "duration_ms": duration_ms,
            "only_missing": only_missing,
        },
    )

    return summary


def run_compliance_resolution_for_existing_db(
    batch_size: int = 1000,
    max_batches: int = 100,
) -> dict:
    started = perf_counter()
    initial_missing = count_jobs_missing_compliance()

    if initial_missing == 0:
        return {
            "initial_missing": 0,
            "remaining_missing": 0,
            "prepared": 0,
            "checked": 0,
            "updated": 0,
            "batches": 0,
            "duration_ms": 0,
        }

    prepared_total = 0
    checked_total = 0
    updated_total = 0
    batches = 0

    for _ in range(max_batches):
        batches += 1

        prepared = backfill_missing_compliance_classes(limit=batch_size)
        prepared_total += prepared

        summary = run_compliance_resolution(limit=batch_size, only_missing=True)
        checked_total += summary.get("checked", 0)
        updated_total += summary.get("updated", 0)

        remaining_missing = count_jobs_missing_compliance()
        if remaining_missing == 0:
            break
        if prepared == 0 and summary.get("updated", 0) == 0:
            break
    else:
        remaining_missing = count_jobs_missing_compliance()

    duration_ms = int((perf_counter() - started) * 1000)
    result = {
        "initial_missing": initial_missing,
        "remaining_missing": remaining_missing,
        "prepared": prepared_total,
        "checked": checked_total,
        "updated": updated_total,
        "batches": batches,
        "duration_ms": duration_ms,
    }

    logger.info(
        "compliance_bootstrap_summary",
        extra={
            "component": "compliance",
            "phase": "compliance_bootstrap_summary",
            "initial_missing": initial_missing,
            "remaining_missing": remaining_missing,
            "prepared": prepared_total,
            "checked": checked_total,
            "updated": updated_total,
            "batches": batches,
            "duration_ms": duration_ms,
        },
    )

    return result
