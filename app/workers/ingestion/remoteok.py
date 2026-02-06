from datetime import datetime, timezone
import logging

from ingestion.adapters.remoteok_api import RemoteOKApiAdapter
from app.workers.normalization.remoteok import normalize_remoteok_job
from storage.sqlite import init_db, upsert_job

logger = logging.getLogger("openjobseu.ingestion.remoteok")


def run_remoteok_ingestion() -> dict:
    logger.info("remoteok ingestion started")

    init_db()
    actions = []

    persisted = 0

    try:
        adapter = RemoteOKApiAdapter()
        entries = adapter.fetch()

        for raw in entries:
            job = normalize_remoteok_job(raw)
            if not job:
                continue

            upsert_job(job)
            persisted += 1

        actions.append(f"remoteok_ingested:{persisted}")

        logger.info(
            "remoteok ingestion completed",
            extra={"persisted": persisted},
        )

    except Exception as exc:
        actions.append("remoteok_ingestion_failed")
        logger.error("remoteok ingestion failed", exc_info=exc)

    return {
        "actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
