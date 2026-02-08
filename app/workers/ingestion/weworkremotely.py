from datetime import datetime, timezone
import logging

from ingestion.adapters.weworkremotely_rss import WeWorkRemotelyRssAdapter
from app.workers.normalization.weworkremotely import (
    normalize_weworkremotely_job,
)
from storage.sqlite import init_db, upsert_job

logger = logging.getLogger("openjobseu.ingestion.weworkremotely")

RSS_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"


def run_weworkremotely_ingestion() -> dict:
    logger.info("weworkremotely ingestion started")

    init_db()
    actions = []
    persisted = 0

    try:
        adapter = WeWorkRemotelyRssAdapter(RSS_URL)
        entries = adapter.fetch()

        for raw in entries:
            job = normalize_weworkremotely_job(raw)
            if not job:
                continue

            upsert_job(job)
            persisted += 1

        actions.append(f"weworkremotely_ingested:{persisted}")

        logger.info(
            "weworkremotely ingestion completed",
            extra={
                "source": "weworkremotely",
                "persisted": persisted,
            },
        )

    except Exception as exc:
        actions.append("weworkremotely_ingestion_failed")
        logger.error("weworkremotely ingestion failed", exc_info=exc)

    return {
        "actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
