import logging
from datetime import datetime, timezone
import sys
from time import perf_counter
from typing import Any

from app.utils.tick_context import reset_current_tick_context, set_current_tick_context
from app.workers.ingestion.employer import run_employer_ingestion
from app.workers.availability import run_availability_pipeline
from app.workers.lifecycle import run_lifecycle_pipeline
from app.workers.market_metrics import run_market_metrics_worker
from app.workers.maintenance import run_maintenance_pipeline
from app.workers.frontend_exporter import run_frontend_export

logger = logging.getLogger("openjobseu.pipeline")

# NOTE: We store the callable names as strings so that tests can monkeypatch the
# functions on the ``pipeline`` module. If we stored the callables directly, the
# references would be bound at import time and monkeypatching would have no
# effect, causing the orchestration order tests to fail.
PIPELINE_STEPS_INGESTION = [
    ("ingestion", "run_employer_ingestion"),
]

PIPELINE_STEPS_MAINTENANCE = [
    ("lifecycle", "run_lifecycle_pipeline"),
    ("availability", "run_availability_pipeline"),
    ("market_metrics", "run_market_metrics_worker"),
    ("maintenance", "run_maintenance_pipeline"),
    ("frontend_export", "run_frontend_export"),
]


def _int_metric(value, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def run_pipeline(group: str = "all", context: dict[str, Any] | None = None) -> dict:
    """
    Execute full tick pipeline using declarative steps.
    Group can be 'all', 'ingestion', or 'maintenance'.
    """
    context = dict(context or {})
    tick_started_at = datetime.now(timezone.utc).isoformat()
    tick_started_perf = perf_counter()
    token = set_current_tick_context(context)

    actions = []
    metrics = {}

    steps = []
    if group in ("all", "ingestion"):
        steps.extend(PIPELINE_STEPS_INGESTION)
    if group in ("all", "maintenance"):
        steps.extend(PIPELINE_STEPS_MAINTENANCE)

    logger.info(
        "tick_pipeline_started",
        extra={
            "component": "pipeline",
            "phase": "tick_pipeline_started",
            "group": group,
            **context,
        },
    )

    try:
        for step_name, step_fn_name in steps:
            try:
                step_callable = getattr(sys.modules[__name__], step_fn_name)
                result = step_callable() or {}

                actions.extend(result.get("actions", []))

                if "metrics" in result:
                    metrics[step_name] = result["metrics"]

            except Exception as e:
                logger.exception(
                    f"Step {step_name} failed: {e}",
                    extra={"step": step_name, "group": group, **context},
                )
                metrics[step_name] = {"status": "error", **context}
    finally:
        reset_current_tick_context(token)

    tick_finished_at = datetime.now(timezone.utc).isoformat()
    tick_duration_ms = int((perf_counter() - tick_started_perf) * 1000)

    metric_values = [m for m in metrics.values() if isinstance(m, dict)]
    sources_ok = sum(1 for m in metric_values if m.get("status") == "ok")
    sources_failed = len(metric_values) - sources_ok
    persisted_count = sum(_int_metric(m.get("persisted_count")) for m in metric_values)

    logger.info(
        "tick_finished",
        extra={
            "component": "pipeline",
            "phase": "tick_finished",
            "pipeline_status": "pipeline_completed",
            "group": group,
            "tick_started_at": tick_started_at,
            "tick_finished_at": tick_finished_at,
            "total_duration_ms": tick_duration_ms,
            "sources_ok": sources_ok,
            "sources_failed": sources_failed,
            "persisted_count": persisted_count,
            **context,
        },
    )

    final_metrics = {
        "status": "completed",
        "phase": "pipeline_completed",
        "group": group,
        "tick_started_at": tick_started_at,
        "tick_finished_at": tick_finished_at,
        "tick_duration_ms": tick_duration_ms,
        **context,
        **metrics,
    }

    return {
        "tick_id": context.get("tick_id"),
        "request_id": context.get("request_id"),
        "scheduler_execution": context.get("scheduler_execution"),
        "actions": actions,
        "metrics": final_metrics,
    }
