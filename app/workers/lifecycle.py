from datetime import datetime, timedelta, timezone
from storage.sqlite import get_jobs_for_verification, update_job_availability
import logging


logger = logging.getLogger("openjobseu.lifecycle")

STALE_AFTER_DAYS = 7
EXPIRE_AFTER_DAYS = 30
MAX_FAILURES = 3
NEW_AFTER_HOURS = 24


def apply_lifecycle_rules(job: dict, now: datetime) -> str | None:
    """
    Decide whether a job should transition to a new lifecycle status.

    Returns:
        - new status string if transition should occur
        - None if no change
    """
    status = job.get("status")
    failures = job.get("verification_failures", 0)


    # Handling NEW jobs
    if status == "new":
        first_seen = job.get("first_seen_at")
        if not first_seen:
            return None

        first_seen_dt = datetime.fromisoformat(first_seen)
        if now - first_seen_dt > timedelta(hours=NEW_AFTER_HOURS):
            return "active"

        return None


    # Never touch already expired jobs
    if status == "expired":
        return None

    # Expire aggressively on repeated failures
    if failures >= MAX_FAILURES:
        return "expired"


    last_verified = job.get("last_verified_at")
    if not last_verified:
        return None

    last_verified_dt = datetime.fromisoformat(last_verified)

    if now - last_verified_dt > timedelta(days=EXPIRE_AFTER_DAYS):
        return "expired"

    if now - last_verified_dt > timedelta(days=STALE_AFTER_DAYS):
        if status == "active":
            return "stale"

    return None


def run_lifecycle_rules() -> None:
    """
    Apply lifecycle rules to all eligible jobs.
    """
    now = datetime.now(timezone.utc)

    jobs = get_jobs_for_lifecycle(limit=50)

    for job in jobs:
        new_status = apply_lifecycle_rules(job, now)

        if new_status:
            update_job_availability(
                job_id=job["job_id"],
                status=new_status,
                verified_at=now.isoformat(),
                failure=False,
            )



def run_lifecycle_pipeline() -> None:
    jobs = get_jobs_for_verification(limit=50)
    now = datetime.now(timezone.utc)

    for job in jobs:
        new_status = apply_lifecycle_rules(job, now)
        if new_status:
            update_job_availability(
                job_id=job["job_id"],
                status=new_status,
                verified_at=now.isoformat(),
                failure=False,
            )

    logger.info("lifecycle pipeline completed")
