from datetime import datetime, timezone
import logging

from ingestion.adapters.weworkremotely_rss import WeWorkRemotelyRssAdapter
from storage.sqlite import init_db, upsert_job

logger = logging.getLogger("openjobseu.tick")

RSS_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"


def run_weworkremotely_ingestion() -> dict:
    logger.info("weworkremotely ingestion started")

    init_db()
    actions = []

    try:
        adapter = WeWorkRemotelyRssAdapter(RSS_URL)
        entries = adapter.fetch()
        jobs = [adapter.normalize(e) for e in entries]

        for job in jobs:
            upsert_job(job)

        actions.append(f"weworkremotely_ingested:{len(jobs)}")

        logger.info(
            "weworkremotely ingestion completed",
            extra={"source": "weworkremotely", "ingested": len(jobs)},
        )

    except Exception as exc:
        actions.append("weworkremotely_ingestion_failed")
        logger.error("weworkremotely ingestion failed", exc_info=exc)

    return {
        "actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
