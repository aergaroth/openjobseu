from datetime import datetime, timezone
import logging

from ingestion.loaders.local_json import load_local_jobs

logger = logging.getLogger("openjobseu.worker.tick")


def run_tick():
    logger.info("tick worker started")

    actions = []

    # Ingestion: local JSON source (temporary)
    try:
        jobs = load_local_jobs("ingestion/sources/example_jobs.json")
        actions.append(f"ingested:{len(jobs)}")
        logger.info("jobs ingested", extra={"count": len(jobs)})
    except Exception as exc:
        actions.append("ingestion_failed")
        logger.error("job ingestion failed", exc_info=exc)

    result = {
        "actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    logger.info("tick worker finished", extra=result)
    return result
