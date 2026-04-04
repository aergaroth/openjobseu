import logging
import os
import uuid
from time import perf_counter

from app.utils.backfill_compliance import backfill_missing_compliance_classes
from app.utils.backfill_department import backfill_missing_departments
from app.utils.backfill_salary import backfill_missing_salary_fields
from app.utils.cloud_tasks import create_tick_task, is_tick_queue_configured
from storage.repositories.maintenance_repository import (
    update_company_stats_and_posture_bulk,
    update_company_signal_scores_bulk,
)

logger = logging.getLogger("openjobseu.maintenance")


def _lag_warning_threshold_ms() -> int:
    raw = os.getenv("MAINTENANCE_LAG_WARNING_MS", "60000")
    try:
        parsed = int(raw)
        return parsed if parsed > 0 else 60000
    except (TypeError, ValueError):
        return 60000


def _update_company_stats_and_posture() -> int:
    """
    Single-pass update for per-company job statistics and remote posture.

    Replaces the former separate `_update_company_job_stats` and
    `_update_company_remote_posture` calls. One scan of `jobs`, one UPDATE
    on `companies` per batch — covers:
      - approved_jobs_count, rejected_jobs_count, total_jobs_count, last_active_job_at
      - remote_posture upgrade (UNKNOWN → REMOTE_FRIENDLY when remote_cnt >= 3)
    """
    return update_company_stats_and_posture_bulk()


def _update_company_signal_scores() -> int:
    """
    Updates the signal_score for all companies based on rules:
    - Remote posture (REMOTE_ONLY: 40, REMOTE_FRIENDLY: 20)
    - EU entity verified: 25
    - HQ in EU: 20
    - Historical approval ratio (>= 80%: 15, >= 50%: 8)
    """
    return update_company_signal_scores_bulk()


_BACKFILL_SALARY_LIMIT = 5000


def _run_backfill_salary() -> int:
    """
    Backfills missing salary fields — one pass of up to BACKFILL_SALARY_LIMIT records.
    Enqueues a Cloud Task continuation only if the limit was hit AND progress was made.
    Without the progress check, runs with no parseable salaries would loop indefinitely.
    """
    result = backfill_missing_salary_fields(limit=_BACKFILL_SALARY_LIMIT)
    if result["processed"] >= _BACKFILL_SALARY_LIMIT and result["updated"] > 0 and is_tick_queue_configured():
        _enqueue_backfill_continuation("backfill-salary", _BACKFILL_SALARY_LIMIT)
    return result["updated"]


def _run_backfill_department() -> int:
    """
    Backfills missing department fields by re-fetching from ATS.
    """
    return backfill_missing_departments()


_BACKFILL_COMPLIANCE_LIMIT = 5000


def _enqueue_backfill_continuation(task_name: str, limit: int) -> None:
    """Enqueue a Cloud Task to continue a backfill job that hit its per-tick record cap."""
    base_url = os.getenv("BASE_URL", "").rstrip("/")
    if not base_url:
        logger.warning(
            "backfill_continuation_skipped",
            extra={"reason": "BASE_URL not set", "task": task_name},
        )
        return
    handler_url = f"{base_url}/internal/tasks/{task_name}/execute"
    try:
        create_tick_task(
            task_id=str(uuid.uuid4()),
            handler_url=handler_url,
            payload={"limit": limit},
            headers={"Content-Type": "application/json"},
        )
        logger.info(
            "backfill_continuation_enqueued",
            extra={"task": task_name, "limit": limit},
        )
    except Exception:
        logger.error(
            "backfill_continuation_enqueue_failed",
            extra={"task": task_name},
            exc_info=True,
        )


def _run_backfill_compliance() -> int:
    """
    Backfills missing compliance fields for jobs — one pass of up to BACKFILL_COMPLIANCE_LIMIT.
    If the limit is reached (more records likely remain), enqueues a Cloud Task continuation
    so the next batch runs in a fresh request rather than extending this tick's runtime.
    """
    count = backfill_missing_compliance_classes(limit=_BACKFILL_COMPLIANCE_LIMIT)
    if count >= _BACKFILL_COMPLIANCE_LIMIT and is_tick_queue_configured():
        _enqueue_backfill_continuation("backfill-compliance", _BACKFILL_COMPLIANCE_LIMIT)
    return count


def run_maintenance_pipeline() -> dict:
    started = perf_counter()
    metrics = {
        "company_stats_updated": 0,
        "scores_updated": 0,
        "salary_backfilled": 0,
        "department_backfilled": 0,
        "compliance_backfilled": 0,
    }

    try:
        # Company-level updates — single scan of `jobs` for stats + posture, then signal score
        metrics["company_stats_updated"] = _update_company_stats_and_posture()
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
