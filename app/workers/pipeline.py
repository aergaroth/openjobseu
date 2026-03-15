import logging
from datetime import datetime, timezone
import sys
from time import perf_counter

from app.workers.ingestion.employer import run_employer_ingestion
from app.workers.availability import run_availability_pipeline
from app.workers.lifecycle import run_lifecycle_pipeline
from app.workers.market_metrics import run_market_metrics_worker
from app.workers.maintenance import run_maintenance_pipeline

logger = logging.getLogger("openjobseu.pipeline")

# NOTE: We store the callable names as strings so that tests can monkeypatch the
# functions on the ``pipeline`` module. If we stored the callables directly, the
# references would be bound at import time and monkeypatching would have no
# effect, causing the orchestration order tests to fail.
PIPELINE_STEPS = [
    ("ingestion", "run_employer_ingestion"),
    ("lifecycle", "run_lifecycle_pipeline"),
    ("availability", "run_availability_pipeline"),
    ("market_metrics", "run_market_metrics_worker"),
    ("maintenance", "run_maintenance_pipeline"),
]

def _int_metric(value, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def run_pipeline() -> dict:
    """
    Execute full tick pipeline using declarative steps
    """
    tick_started_at = datetime.now(timezone.utc).isoformat()
    tick_started_perf = perf_counter()

    actions = []
    metrics = {}

    for step_name, step_fn_name in PIPELINE_STEPS:
        try:
            step_callable = getattr(sys.modules[__name__], step_fn_name)
            result = step_callable() or {}

            actions.extend(result.get("actions", []))

            if "metrics" in result:
                metrics[step_name] = result["metrics"]

        except Exception as e:
            logger.exception(f"Step {step_name} failed: {e}")
            metrics[step_name] = {"status": "error"}

    tick_finished_at = datetime.now(timezone.utc).isoformat()
    tick_duration_ms = int((perf_counter() - tick_started_perf) * 1000)

    # Aggregate metrics for logging
    metric_values = [m for m in metrics.values() if isinstance(m, dict)]
    sources_ok = sum(1 for m in metric_values if m.get("status") == "ok")
    sources_failed = len(metric_values) - sources_ok
    persisted_count = sum(
        _int_metric(m.get("persisted_count")) for m in metric_values
    )

    logger.info(
        "tick_finished",
        extra={
            "component": "pipeline",
            "phase": "tick_finished",
            "tick_started_at": tick_started_at,
            "tick_finished_at": tick_finished_at,
            "total_duration_ms": tick_duration_ms,
            "sources_ok": sources_ok,
            "sources_failed": sources_failed,
            "persisted_count": persisted_count,
        },
    )

    final_metrics = {
        "tick_started_at": tick_started_at,
        "tick_finished_at": tick_finished_at,
        "tick_duration_ms": tick_duration_ms,
        **metrics,
    }

    return {
        "actions": actions,
        "metrics": final_metrics,
    }