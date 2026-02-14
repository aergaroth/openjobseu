import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Iterable, Dict, Callable, List

from app.workers.post_ingestion import run_post_ingestion

logger = logging.getLogger("openjobseu.pipeline")


def _int_metric(value, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _policy_metrics(source_metrics: dict | None = None) -> dict:
    source_metrics = source_metrics or {}
    by_reason = source_metrics.get("policy_rejected_by_reason") or {}
    non_remote = _int_metric(by_reason.get("non_remote", 0))
    geo_restriction = _int_metric(by_reason.get("geo_restriction", 0))
    rejected_total = _int_metric(
        source_metrics.get(
            "policy_rejected_total",
            source_metrics.get("rejected_policy_count", non_remote + geo_restriction),
        )
    )
    return {
        "rejected_total": rejected_total,
        "by_reason": {
            "non_remote": non_remote,
            "geo_restriction": geo_restriction,
        },
    }


def run_tick_pipeline(
    *,
    ingestion_sources: Iterable[str],
    ingestion_handlers: Dict[str, Callable[[], dict]],
) -> dict:
    """
    Execute full tick pipeline:
    ingestion → post_ingestion
    """

    requested_sources = list(ingestion_sources)
    tick_started_at = datetime.now(timezone.utc).isoformat()
    tick_started_perf = perf_counter()

    actions: List[str] = []
    per_source: Dict[str, dict] = {}

    totals = {
        "sources_ok": 0,
        "sources_failed": 0,
        "sources_unknown": 0,
        "raw_count": 0,
        "persisted_count": 0,
        "skipped_count": 0,
    }

    # --- Ingestion phase ---
    for source in requested_sources:
        handler = ingestion_handlers.get(source)
        source_started_perf = perf_counter()

        if not handler:
            logger.warning("unknown ingestion source", extra={"source": source})
            totals["sources_unknown"] += 1
            per_source[source] = {
                "status": "unknown",
                "raw_count": 0,
                "persisted_count": 0,
                "skipped_count": 0,
                "policy": _policy_metrics(),
                "duration_ms": int((perf_counter() - source_started_perf) * 1000),
            }
            continue

        try:
            result = handler()
            actions.extend(result.get("actions", []))
            source_metrics = result.get("metrics", {})

            raw_count = _int_metric(source_metrics.get("raw_count", 0))
            persisted_count = _int_metric(source_metrics.get("persisted_count", 0))
            skipped_count = _int_metric(source_metrics.get("skipped_count", 0))
            duration_ms = _int_metric(
                source_metrics.get(
                    "duration_ms",
                    int((perf_counter() - source_started_perf) * 1000),
                )
            )

            source_status = source_metrics.get("status", "ok")
            per_source[source] = {
                "status": source_status,
                "raw_count": raw_count,
                "persisted_count": persisted_count,
                "skipped_count": skipped_count,
                "policy": _policy_metrics(source_metrics),
                "duration_ms": duration_ms,
            }

            if source_status == "ok":
                totals["sources_ok"] += 1
            else:
                totals["sources_failed"] += 1
            totals["raw_count"] += raw_count
            totals["persisted_count"] += persisted_count
            totals["skipped_count"] += skipped_count
        except Exception:
            logger.exception("ingestion source failed", extra={"source": source})
            totals["sources_failed"] += 1
            per_source[source] = {
                "status": "failed",
                "raw_count": 0,
                "persisted_count": 0,
                "skipped_count": 0,
                "policy": _policy_metrics(),
                "duration_ms": int((perf_counter() - source_started_perf) * 1000),
            }

    # --- Post-ingestion (availability + lifecycle) ---
    run_post_ingestion()

    tick_finished_at = datetime.now(timezone.utc).isoformat()
    tick_duration_ms = int((perf_counter() - tick_started_perf) * 1000)

    metrics = {
        "tick_started_at": tick_started_at,
        "tick_finished_at": tick_finished_at,
        "tick_duration_ms": tick_duration_ms,
        "ingestion": {
            "sources_total": len(requested_sources),
            "sources_ok": totals["sources_ok"],
            "sources_failed": totals["sources_failed"],
            "sources_unknown": totals["sources_unknown"],
            "raw_count": totals["raw_count"],
            "persisted_count": totals["persisted_count"],
            "skipped_count": totals["skipped_count"],
            "per_source": per_source,
        },
    }

    logger.info(
        "tick",
        extra={
            "component": "pipeline",
            "phase": "tick_finished",
            "total_duration_ms": tick_duration_ms,
            "sources_ok": totals["sources_ok"],
            "sources_failed": totals["sources_failed"],
            "persisted_count": totals["persisted_count"],
        },
    )

    return {
        "actions": actions,
        "metrics": metrics,
    }
