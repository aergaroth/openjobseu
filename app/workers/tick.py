from datetime import datetime, timezone
import logging

from ingestion.loaders.local_json import load_local_jobs
from ingestion.adapters.rss_feed import RssFeedAdapter
from ingestion.adapters.remotive_api import RemotiveApiAdapter

from storage.sqlite import init_db, upsert_job

from storage.sqlite import (
    get_jobs_for_verification,
    update_job_availability,
)
from app.workers.availability import (
    check_job_availability,
)
from app.workers.lifecycle import apply_lifecycle_rules


logger = logging.getLogger("openjobseu.tick")


def run_tick():

    '''
    Dev-only tick using local JSON source.
    '''

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

RSS_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"


def run_remotive_tick():
    logger.info("remotive tick worker started")

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
            extra={
                "source": "remotive",
                "ingested": len(jobs),
            }
        )

        logger.info(
            "jobs persisted",
            extra={
                "count": len(jobs),
                "storage": "sqlite",
            }
        )

    except Exception as exc:
        actions.append("remotive_ingestion_failed")
        logger.error("remotive ingestion failed", exc_info=exc)

    result = {
        "actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "remotive tick finished",
        extra=result,
    )

    return result
