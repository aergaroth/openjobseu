from datetime import datetime, timezone
import logging

from ingestion.adapters.remotive_api import RemotiveApiAdapter
from storage.sqlite import init_db, upsert_job

logger = logging.getLogger("openjobseu.tick")


def run_remotive_ingestion() -> dict:
    logger.info("remotive ingestion started")

    init_db()
    actions = []

    try:
        adapter = RemotiveApiAdapter()
        entries = adapter.fetch()
        jobs = [adapter.normalize(e) for e in entries]

        for job in jobs:
            upsert_job(job)

        actions.append(f"remotive_ingested:{len(jobs)}")

        logger.info(
            "remotive ingestion completed",
            extra={"source": "remotive", "ingested": len(jobs)},
        )

    except Exception as exc:
        actions.append("remotive_ingestion_failed")
        logger.error("remotive ingestion failed", exc_info=exc)

    return {
        "actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
