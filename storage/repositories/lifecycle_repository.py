from sqlalchemy import text
from sqlalchemy.engine import Connection

def expire_jobs_due_to_lifecycle(conn: Connection) -> int:
    """
    Expire jobs that have too many verification failures or are too old.

    This corresponds to EXPIRE_AFTER_DAYS and MAX_FAILURES settings.
    Returns the number of affected rows.
    """
    result = conn.execute(
        text("""
            UPDATE jobs
            SET status = 'expired',
                updated_at = NOW()
            WHERE status != 'expired'
            AND (
                verification_failures >= 3
                OR availability_status = 'expired'
                OR (last_verified_at IS NOT NULL AND last_verified_at < NOW() - INTERVAL '30 days')
            )
        """)
    )
    return result.rowcount


def stale_active_jobs_due_to_lifecycle(conn: Connection) -> int:
    """
    Transition active jobs to stale if they haven't been verified recently.

    This corresponds to STALE_AFTER_DAYS setting.
    Returns the number of affected rows.
    """
    result = conn.execute(
        text("""
            UPDATE jobs
            SET status = 'stale',
                updated_at = NOW()
            WHERE status = 'active'
            AND last_verified_at IS NOT NULL
            AND last_verified_at < NOW() - INTERVAL '7 days'
        """)
    )
    return result.rowcount


def activate_new_jobs_due_to_lifecycle(conn: Connection) -> int:
    """
    Transition new jobs to active after a certain period.

    This corresponds to NEW_AFTER_HOURS setting.
    Returns the number of affected rows.
    """
    result = conn.execute(
        text("""
            UPDATE jobs
            SET status = 'active',
                updated_at = NOW()
            WHERE status = 'new'
            AND first_seen_at < NOW() - INTERVAL '24 hours'
        """)
    )
    return result.rowcount


def reactivate_stale_jobs_due_to_lifecycle(conn: Connection) -> int:
    """
    Transition stale jobs back to active if they have been verified recently.
    This acts as a healing mechanism for data consistency.
    Returns the number of affected rows.
    """
    result = conn.execute(
        text("""
            UPDATE jobs
            SET status = 'active',
                updated_at = NOW()
            WHERE status = 'stale'
            AND availability_status = 'active'
            AND last_verified_at IS NOT NULL
            AND last_verified_at >= NOW() - INTERVAL '7 days'
        """)
    )
    return result.rowcount


def mark_reposts_due_to_lifecycle(conn: Connection, *, days_threshold: int = 30) -> int:
    """
    Mark jobs as reposts when there is a previous job with the same
    fingerprint + company + title whose last_seen_at is within threshold days.
    Also stores how many qualifying previous jobs were found.
    """
    result = conn.execute(
        text("""
            UPDATE jobs j
            SET
                is_repost = CASE WHEN COALESCE(matches.repost_count, 0) > 0 THEN TRUE ELSE FALSE END,
                repost_count = COALESCE(matches.repost_count, 0),
                updated_at = NOW()
            FROM (
                SELECT
                    cur.job_id,
                    COUNT(prev.job_id) AS repost_count
                FROM jobs cur
                LEFT JOIN jobs prev
                  ON cur.job_fingerprint = prev.job_fingerprint
                 AND cur.company_name = prev.company_name
                 AND cur.title = prev.title
                 AND cur.job_id <> prev.job_id
                 AND cur.first_seen_at > prev.last_seen_at
                 AND cur.first_seen_at - prev.last_seen_at < (:days_threshold * INTERVAL '1 day')
                GROUP BY cur.job_id
            ) matches
            WHERE j.job_id = matches.job_id
              AND (
                  COALESCE(j.repost_count, 0) <> COALESCE(matches.repost_count, 0)
                  OR j.is_repost <> (COALESCE(matches.repost_count, 0) > 0)
              )
        """),
        {"days_threshold": int(days_threshold)},
    )
    return result.rowcount
