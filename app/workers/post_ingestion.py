from datetime import datetime, timezone
import logging

from storage.sqlite import (
    get_jobs_for_verification,
    update_job_availability,
)
from app.workers.availability import check_job_availability
from app.workers.lifecycle import apply_lifecycle_rules

logger = logging.getLogger("openjobseu.tick")


def run_post_ingestion(actions: list) -> None:
    # Availability (A3)
    try:
        jobs = get_jobs_for_verification(limit=50)
        now = datetime.now(timezone.utc).isoformat()

        stats = {
            "checked": 0,
            "active": 0,
            "expired": 0,
            "unreachable": 0,
        }

        for job in jobs:
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

        logger.info("availability completed", extra=stats)

    except Exception as exc:
        actions.append("availability_failed")
        logger.error("availability failed", exc_info=exc)

    # Lifecycle (A4)
    try:
        now_dt = datetime.now(timezone.utc)

        lifecycle_stats = {
            "stale": 0,
            "expired": 0,
        }

        jobs = get_jobs_for_verification(limit=50)

        for job in jobs:
            new_status = apply_lifecycle_rules(job, now_dt)
            if new_status:
                update_job_availability(
                    job_id=job["job_id"],
                    status=new_status,
                    verified_at=now_dt.isoformat(),
                    failure=False,
                )
                lifecycle_stats[new_status] += 1

        if lifecycle_stats["stale"] or lifecycle_stats["expired"]:
            actions.append(
                f"lifecycle:stale={lifecycle_stats['stale']},expired={lifecycle_stats['expired']}"
            )

        logger.info("lifecycle completed", extra=lifecycle_stats)

    except Exception as exc:
        actions.append("lifecycle_failed")
        logger.error("lifecycle failed", exc_info=exc)
