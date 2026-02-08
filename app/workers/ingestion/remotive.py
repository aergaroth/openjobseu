from datetime import datetime, timezone
import logging

from ingestion.adapters.remotive_api import RemotiveApiAdapter
from app.workers.normalization.remotive import normalize_remotive_job
from storage.sqlite import init_db, upsert_job

logger = logging.getLogger("openjobseu.ingestion.remotive")


def run_remotive_ingestion() -> dict:
    logger.info("remotive ingestion started")

    init_db()
    actions = []
    persisted = 0

    try:
        adapter = RemotiveApiAdapter()
        entries = adapter.fetch()

        for raw in entries:
            job = normalize_remotive_job(raw)
            if not job:
                continue

            upsert_job(job)
            persisted += 1

        actions.append(f"remotive_ingested:{persisted}")

        logger.info(
            "remotive ingestion completed",
            extra={
                "source": "remotive",
                "persisted": persisted,
            },
        )

    except Exception as exc:
        actions.append("remotive_ingestion_failed")
        logger.error("remotive ingestion failed", exc_info=exc)

    return {
        "actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
