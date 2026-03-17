from sqlalchemy import text
from storage.db_engine import get_engine


def expire_jobs_due_to_lifecycle() -> int:
    """
    Expire jobs that have too many verification failures or are too old.

    This corresponds to EXPIRE_AFTER_DAYS and MAX_FAILURES settings.
    Returns the number of affected rows.
    """
    engine = get_engine()
    batch_size = 1000
    total_updated = 0
    while True:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    WITH target_jobs AS (
                        SELECT job_id
                        FROM jobs
                        WHERE status != 'expired'
                        AND (
                            verification_failures >= 3
                            OR availability_status = 'expired'
                            OR (last_verified_at IS NOT NULL AND last_verified_at < NOW() - INTERVAL '30 days')
                        )
                        LIMIT :batch_size
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE jobs
                    SET status = 'expired',
                        updated_at = NOW()
                    FROM target_jobs
                    WHERE jobs.job_id = target_jobs.job_id
                """),
                {"batch_size": batch_size}
            )
            total_updated += result.rowcount
            if result.rowcount == 0:
                break
    return total_updated


def stale_active_jobs_due_to_lifecycle() -> int:
    """
    Transition active jobs to stale if they haven't been verified recently.

    This corresponds to STALE_AFTER_DAYS setting.
    Returns the number of affected rows.
    """
    engine = get_engine()
    batch_size = 1000
    total_updated = 0
    while True:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    WITH target_jobs AS (
                        SELECT job_id
                        FROM jobs
                        WHERE status = 'active'
                        AND last_verified_at IS NOT NULL
                        AND last_verified_at < NOW() - INTERVAL '7 days'
                        LIMIT :batch_size
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE jobs
                    SET status = 'stale',
                        updated_at = NOW()
                    FROM target_jobs
                    WHERE jobs.job_id = target_jobs.job_id
                """),
                {"batch_size": batch_size}
            )
            total_updated += result.rowcount
            if result.rowcount == 0:
                break
    return total_updated


def activate_new_jobs_due_to_lifecycle() -> int:
    """
    Transition new jobs to active after a certain period.

    This corresponds to NEW_AFTER_HOURS setting.
    Returns the number of affected rows.
    """
    engine = get_engine()
    batch_size = 1000
    total_updated = 0
    while True:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    WITH target_jobs AS (
                        SELECT job_id
                        FROM jobs
                        WHERE status = 'new'
                        AND first_seen_at < NOW() - INTERVAL '24 hours'
                        LIMIT :batch_size
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE jobs
                    SET status = 'active',
                        updated_at = NOW()
                    FROM target_jobs
                    WHERE jobs.job_id = target_jobs.job_id
                """),
                {"batch_size": batch_size}
            )
            total_updated += result.rowcount
            if result.rowcount == 0:
                break
    return total_updated


def reactivate_stale_jobs_due_to_lifecycle() -> int:
    """
    Transition stale jobs back to active if they have been verified recently.
    This acts as a healing mechanism for data consistency.
    Returns the number of affected rows.
    """
    engine = get_engine()
    batch_size = 1000
    total_updated = 0
    while True:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    WITH target_jobs AS (
                        SELECT job_id
                        FROM jobs
                        WHERE status = 'stale'
                        AND availability_status = 'active'
                        AND last_verified_at IS NOT NULL
                        AND last_verified_at >= NOW() - INTERVAL '7 days'
                        LIMIT :batch_size
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE jobs
                    SET status = 'active',
                        updated_at = NOW()
                    FROM target_jobs
                    WHERE jobs.job_id = target_jobs.job_id
                """),
                {"batch_size": batch_size}
            )
            total_updated += result.rowcount
            if result.rowcount == 0:
                break
    return total_updated


def mark_reposts_due_to_lifecycle(*, days_threshold: int = 30) -> int:
    """
    Mark jobs as reposts when there is a previous job with the same
    fingerprint + company + title whose last_seen_at is within threshold days.
    Also stores how many qualifying previous jobs were found.
    """
    engine = get_engine()
    batch_size = 1000
    total_updated = 0
    while True:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    WITH target_jobs AS (
                        SELECT
                            cur.job_id,
                            COUNT(prev.job_id) AS new_repost_count
                        FROM jobs cur
                        LEFT JOIN jobs prev
                          ON cur.job_fingerprint = prev.job_fingerprint
                         AND cur.company_name = prev.company_name
                         AND cur.title = prev.title
                         AND cur.job_id <> prev.job_id
                         AND cur.first_seen_at > prev.last_seen_at
                         AND cur.first_seen_at - prev.last_seen_at < (:days_threshold * INTERVAL '1 day')
                        -- OPTYMALIZACJA: Bada status "repost" tylko dla ofert dodanych w ciagu ostatnich X dni.
                        WHERE cur.first_seen_at > NOW() - ((:days_threshold + 15) * INTERVAL '1 day')
                        GROUP BY cur.job_id, cur.repost_count, cur.is_repost
                        HAVING COALESCE(cur.repost_count, 0) <> COUNT(prev.job_id)
                            OR cur.is_repost <> (COUNT(prev.job_id) > 0)
                        LIMIT :batch_size
                    )
                    UPDATE jobs j
                    SET
                        is_repost = CASE WHEN target_jobs.new_repost_count > 0 THEN TRUE ELSE FALSE END,
                        repost_count = target_jobs.new_repost_count,
                        updated_at = NOW()
                    FROM target_jobs
                    WHERE j.job_id = target_jobs.job_id
                """),
                {"days_threshold": int(days_threshold), "batch_size": batch_size},
            )
            total_updated += result.rowcount
            if result.rowcount == 0:
                break
    return total_updated
