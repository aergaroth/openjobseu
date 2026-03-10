import logging
from datetime import datetime, timezone
from time import perf_counter

from app.workers.ingestion.employer import run_employer_ingestion
from app.workers.availability import run_availability_pipeline
from app.workers.lifecycle import run_lifecycle_pipeline

logger = logging.getLogger("openjobseu.pipeline")


def _int_metric(value, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def run_pipeline() -> dict:
    """
    Execute full tick pipeline:
    1. ingestion
    2. availability
    3. lifecycle
    """

    tick_started_at = datetime.now(timezone.utc).isoformat()
    tick_started_perf = perf_counter()

    # 1. Ingestion
    employer_result = {"actions": [], "metrics": {"status": "failed"}}
    try:
        employer_result = run_employer_ingestion()
    except Exception:
        logger.exception("employer ingestion failed")

    # 2. Availability
    availability_summary = {}
    try:
        availability_summary = run_availability_pipeline() or {}
    except Exception:
        logger.exception("availability step failed")

    # 3. Lifecycle
    try:
        run_lifecycle_pipeline()
    except Exception:
        logger.exception("lifecycle step failed")

    tick_finished_at = datetime.now(timezone.utc).isoformat()
    tick_duration_ms = int((perf_counter() - tick_started_perf) * 1000)
    ingestion_metrics = employer_result.get("metrics") or {}
    source_status = str(ingestion_metrics.get("status") or "ok").strip().lower()

    metrics = {
        "tick_started_at": tick_started_at,
        "tick_finished_at": tick_finished_at,
        "tick_duration_ms": tick_duration_ms,
        "ingestion": ingestion_metrics,
        "availability": availability_summary,
    }

    logger.info(
        "tick_finished",
        extra={
            "component": "pipeline",
            "phase": "tick_finished",
            "total_duration_ms": tick_duration_ms,
            "sources_ok": 1 if source_status == "ok" else 0,
            "sources_failed": 0 if source_status == "ok" else 1,
            "persisted_count": _int_metric(ingestion_metrics.get("persisted_count", 0)),
        },
    )

    return {
        "actions": list(employer_result.get("actions") or []),
        "metrics": metrics,
    }
