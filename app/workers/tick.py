from datetime import datetime, timezone
import logging
from time import perf_counter

from ingestion.loaders.local_json import load_local_jobs
from app.workers.post_ingestion import run_post_ingestion

logger = logging.getLogger("openjobseu.tick")


def run_tick():
    """
    Dev-only tick using local JSON source.
    """
    logger.info("local tick started")
    tick_started_at = datetime.now(timezone.utc).isoformat()
    tick_started_perf = perf_counter()

    actions = []
    raw_count = 0
    source_status = "ok"
    source_started_perf = perf_counter()
    source_duration_ms = 0

    try:
        jobs = load_local_jobs("ingestion/sources/example_jobs.json")
        raw_count = len(jobs)
        actions.append(f"local_ingested:{raw_count}")
    except Exception as exc:
        actions.append("local_ingestion_failed")
        source_status = "failed"
        logger.error("local ingestion failed", exc_info=exc)
    finally:
        source_duration_ms = int((perf_counter() - source_started_perf) * 1000)

    run_post_ingestion()

    tick_finished_at = datetime.now(timezone.utc).isoformat()
    tick_duration_ms = int((perf_counter() - tick_started_perf) * 1000)

    return {
        "actions": actions,
        "timestamp": tick_finished_at,
        "metrics": {
            "tick_started_at": tick_started_at,
            "tick_finished_at": tick_finished_at,
            "tick_duration_ms": tick_duration_ms,
            "ingestion": {
                "sources_total": 1,
                "sources_ok": 1 if source_status == "ok" else 0,
                "sources_failed": 1 if source_status == "failed" else 0,
                "sources_unknown": 0,
                "raw_count": raw_count,
                "persisted_count": 0,
                "skipped_count": 0,
                "per_source": {
                    "local": {
                        "status": source_status,
                        "raw_count": raw_count,
                        "persisted_count": 0,
                        "skipped_count": 0,
                        "policy": {
                            "rejected_total": 0,
                            "by_reason": {
                                "non_remote": 0,
                                "geo_restriction": 0,
                            },
                        },
                        "remote_model_counts": {
                            "remote_only": 0,
                            "remote_but_geo_restricted": 0,
                            "non_remote": 0,
                            "unknown": 0,
                        },
                        "duration_ms": source_duration_ms,
                    }
                },
            },
        },
    }
