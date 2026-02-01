from datetime import datetime, timezone
import logging
from ingestion.loaders.local_json import load_local_jobs
from ingestion.adapters.rss_feed import RssFeedAdapter
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


def run_rss_tick():
    logger.info("rss tick worker started")

    ## test:
    #logger.info("RSS VERSION MARKER 12345")

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

    # Availability check (A3)
    try:
        jobs_to_check = get_jobs_for_verification(limit=20)

        stats = {
            "checked": 0,
            "active": 0,
            "expired": 0,
            "unreachable": 0,
        }

        now = datetime.now(timezone.utc).isoformat()

        for job in jobs_to_check:
            status = check_job_availability(job)

            update_job_availability(
                job_id=job["job_id"],
                status=status,
                verified_at=now,
                failure=(status == "unreachable"),
            )

            stats["checked"] += 1
            stats[status] += 1

        actions.append(f"availability_checked:{stats['checked']}")

        logger.info(
            "availability check completed",
            extra=stats,
        )

    except Exception as exc:
        actions.append("availability_check_failed")
        logger.error("availability check failed", exc_info=exc)

    # Lifecycle rules (A4)
    try:
        now = datetime.now(timezone.utc)

        lifecycle_stats = {
            "stale": 0,
            "expired": 0,
        }

        jobs_for_lifecycle = get_jobs_for_verification(limit=50)

        for job in jobs_for_lifecycle:
            new_status = apply_lifecycle_rules(job, now)

            if new_status:
                update_job_availability(
                    job_id=job["job_id"],
                    status=new_status,
                    verified_at=now.isoformat(),
                    failure=False,
                )
                lifecycle_stats[new_status] += 1

        if lifecycle_stats["stale"] or lifecycle_stats["expired"]:
            actions.append(
                f"lifecycle:stale={lifecycle_stats['stale']},expired={lifecycle_stats['expired']}"
            )

        logger.info(
            "lifecycle rules applied",
            extra=lifecycle_stats,
        )

    except Exception as exc:
        actions.append("lifecycle_failed")
        logger.error("lifecycle processing failed", exc_info=exc)



    return result
