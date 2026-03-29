import logging
import os
from time import perf_counter

from app.utils.backfill_compliance import backfill_missing_compliance_classes
from app.utils.backfill_department import backfill_missing_departments
from app.utils.backfill_salary import backfill_missing_salary_fields
from storage.repositories.maintenance_repository import (
    update_company_job_stats_bulk,
    update_company_signal_scores_bulk,
    update_company_remote_posture_bulk,
)

logger = logging.getLogger("openjobseu.maintenance")


def _lag_warning_threshold_ms() -> int:
    raw = os.getenv("MAINTENANCE_LAG_WARNING_MS", "60000")
    try:
        parsed = int(raw)
        return parsed if parsed > 0 else 60000
    except (TypeError, ValueError):
        return 60000


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


def _run_backfill_salary() -> int:
    """
    Backfills missing salary fields by re-parsing description and title.
    """
    return backfill_missing_salary_fields(limit=5000)


def _run_backfill_department() -> int:
    """
    Backfills missing department fields by re-fetching from ATS.
    """
    return backfill_missing_departments()


def _run_backfill_compliance() -> int:
    """
    Backfills missing compliance fields for jobs.
    """
    return backfill_missing_compliance_classes(limit=5000)


def run_maintenance_pipeline() -> dict:
    started = perf_counter()
    metrics = {
        "posture_updated": 0,
        "job_stats_updated": 0,
        "scores_updated": 0,
        "salary_backfilled": 0,
        "department_backfilled": 0,
        "compliance_backfilled": 0,
    }

    try:
        # Company-level updates
        metrics["posture_updated"] = _update_company_remote_posture()
        metrics["job_stats_updated"] = _update_company_job_stats()
        metrics["scores_updated"] = _update_company_signal_scores()

        # Job-level backfills
        metrics["salary_backfilled"] = _run_backfill_salary()
        metrics["department_backfilled"] = _run_backfill_department()
        metrics["compliance_backfilled"] = _run_backfill_compliance()

        metrics["status"] = "ok"
    except Exception as e:
        logger.error("maintenance pipeline failed", exc_info=True)
        logger.critical(
            "maintenance_pipeline_critical_error",
            extra={"component": "maintenance", "error": str(e)},
        )
        metrics["status"] = "error"
        metrics["error"] = str(e)

    metrics["duration_ms"] = int((perf_counter() - started) * 1000)

    lag_warning_threshold_ms = _lag_warning_threshold_ms()
    if metrics["duration_ms"] >= lag_warning_threshold_ms:
        logger.warning(
            "maintenance_pipeline_performance_lag",
            extra={
                "component": "maintenance",
                "duration_ms": metrics["duration_ms"],
                "threshold_ms": lag_warning_threshold_ms,
                "status": metrics.get("status"),
            },
        )

    logger.info("maintenance_pipeline_completed", extra={"component": "maintenance", **metrics})

    return {
        "actions": ["maintenance_pipeline_completed"],
        "metrics": metrics,
    }
