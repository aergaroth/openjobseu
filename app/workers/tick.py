from datetime import datetime, timezone
import logging

from ingestion.loaders.local_json import load_local_jobs
from app.workers.post_ingestion import run_post_ingestion

logger = logging.getLogger("openjobseu.tick")


def run_tick():
    """
    Dev-only tick using local JSON source.
    """
    logger.info("local tick started")

    actions = []

    try:
        jobs = load_local_jobs("ingestion/sources/example_jobs.json")
        actions.append(f"local_ingested:{len(jobs)}")
    except Exception as exc:
        actions.append("local_ingestion_failed")
        logger.error("local ingestion failed", exc_info=exc)

    run_post_ingestion()

    return {
        "actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
