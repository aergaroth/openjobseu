from datetime import datetime, timezone
import logging
from ingestion.loaders.local_json import load_local_jobs
from ingestion.adapters.rss_feed import RssFeedAdapter
from storage.sqlite import init_db, upsert_job

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


def run_rss_tick():
    logger.info("rss tick worker started")

    init_db()

    actions = []

    try:
        adapter = RssFeedAdapter(RSS_URL)
        entries = adapter.fetch()
        jobs = [adapter.normalize(e) for e in entries]

        for job in jobs:
            upsert_job(job)

        actions.append(f"persisted:{len(jobs)}")
        actions.append(f"rss_ingested:{len(jobs)}")
 
        logger.info(
            "rss ingestion completed",
            extra={
                "source": "rss",
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
        actions.append("rss_ingestion_failed")
        logger.error("rss ingestion failed", exc_info=exc)

    result = {
        "actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

        logger.info(
            "rss tick finished",
            extra={
                "actions": actions,
            }
        )
    return result
