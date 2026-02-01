from datetime import datetime, timedelta, timezone

STALE_AFTER_DAYS = 7
EXPIRE_AFTER_DAYS = 30
MAX_FAILURES = 3


def apply_lifecycle_rules(job: dict, now: datetime) -> str | None:
    """
    Decide whether a job should transition to a new lifecycle status.

    Returns:
        - new status string if transition should occur
        - None if no change
    """
    status = job.get("status")
    last_verified = job.get("last_verified_at")
    failures = job.get("verification_failures", 0)

    # Never touch already expired jobs
    if status == "expired":
        return None

    # Expire aggressively on repeated failures
    if failures >= MAX_FAILURES:
        return "expired"

    if not last_verified:
        return None

    last_verified_dt = datetime.fromisoformat(last_verified)

    if now - last_verified_dt > timedelta(days=EXPIRE_AFTER_DAYS):
        return "expired"

    if now - last_verified_dt > timedelta(days=STALE_AFTER_DAYS):
        if status == "active":
            return "stale"

    return None
