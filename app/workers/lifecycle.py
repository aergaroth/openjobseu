from datetime import datetime, timedelta, timezone
from storage.db_engine import get_engine
from storage.db_logic import get_jobs_for_verification, update_jobs_availability

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
    Backward-compatible wrapper.
    Apply lifecycle rules to all eligible jobs.
    """
    run_lifecycle_pipeline()



def run_lifecycle_pipeline() -> None:
    # init_db()  # initialized at app startup in app/main.py
    jobs = get_jobs_for_verification(limit=50)
    now = datetime.now(timezone.utc)

    updates: list[dict] = []
    for job in jobs:
        new_status = apply_lifecycle_rules(job, now)
        if not new_status:
            continue

        updates.append(
            {
                "job_id": job["job_id"],
                "status": new_status,
                "verified_at": now,
                "failure": False,
                "updated_at": now,
            }
        )

    if not updates:
        return

    db_engine = get_engine()
    with db_engine.begin() as conn:
        update_jobs_availability(updates=updates, conn=conn)
