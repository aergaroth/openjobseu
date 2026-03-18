import logging
from time import perf_counter

from storage.repositories.maintenance_repository import (
    update_company_job_stats_bulk,
    update_company_signal_scores_bulk,
    update_company_remote_posture_bulk,
)

logger = logging.getLogger("openjobseu.maintenance")


def _update_company_job_stats() -> int:
    """
    Updates aggregated job statistics in the companies table:
    - approved_jobs_count
    - rejected_jobs_count
    - total_jobs_count
    - last_active_job_at
    """
    return update_company_job_stats_bulk()


def _update_company_remote_posture() -> int:
    """
    Upgrades remote_posture from 'UNKNOWN' to 'REMOTE_FRIENDLY'
    for companies that have accumulated at least 3 remote jobs.
    """
    return update_company_remote_posture_bulk()


def _update_company_signal_scores() -> int:
    """
    Updates the signal_score for all companies based on rules:
    - Remote posture (REMOTE_ONLY: 40, REMOTE_FRIENDLY: 20)
    - EU entity verified: 25
    - HQ in EU: 20
    - Historical approval ratio (>= 80%: 15, >= 50%: 8)
    """
    return update_company_signal_scores_bulk()


def run_maintenance_pipeline() -> dict:
    started = perf_counter()
    metrics = {
        "posture_updated": 0,
        "job_stats_updated": 0,
        "scores_updated": 0,
    }

    try:
        metrics["posture_updated"] = _update_company_remote_posture()
        metrics["job_stats_updated"] = _update_company_job_stats()
        metrics["scores_updated"] = _update_company_signal_scores()
        metrics["status"] = "ok"
    except Exception as e:
        logger.error("maintenance pipeline failed", exc_info=True)
        metrics["status"] = "error"
        metrics["error"] = str(e)

    metrics["duration_ms"] = int((perf_counter() - started) * 1000)

    logger.info("maintenance_pipeline_completed", extra={"component": "maintenance", **metrics})

    return {
        "actions": ["maintenance_pipeline_completed"],
        "metrics": metrics,
    }