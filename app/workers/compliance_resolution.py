import logging
from time import perf_counter

from app.workers.compliance_resolver import resolve_compliance
from storage.sqlite import (
    get_jobs_for_compliance_resolution,
    update_job_compliance_resolution,
)

logger = logging.getLogger("openjobseu.compliance")


def run_compliance_resolution(limit: int = 500) -> dict:
    """
    Resolve compliance status and score for persisted jobs.

    This runs after ingestion and before post-ingestion workers.
    """
    started = perf_counter()
    checked = 0
    updated = 0

    try:
        jobs = get_jobs_for_compliance_resolution(limit=limit)
        checked = len(jobs)

        for job in jobs:
            result = resolve_compliance(
                job.get("remote_class"),
                job.get("geo_class"),
            )
            update_job_compliance_resolution(
                job_id=job["job_id"],
                compliance_status=result["compliance_status"],
                compliance_score=int(result["compliance_score"]),
            )
            updated += 1
    except Exception:
        logger.exception("compliance resolution step failed")

    duration_ms = int((perf_counter() - started) * 1000)
    summary = {
        "checked": checked,
        "updated": updated,
        "duration_ms": duration_ms,
    }

    logger.info(
        "compliance_resolution_summary",
        extra={
            "component": "compliance",
            "phase": "compliance_resolution_summary",
            "checked": checked,
            "updated": updated,
            "duration_ms": duration_ms,
        },
    )

    return summary
