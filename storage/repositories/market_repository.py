from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection


def compute_market_stats(conn: Connection, date: date) -> dict:
    start_time = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    end_time = start_time + timedelta(days=1)

    jobs_stats = (
        conn.execute(
            text("""
            SELECT
                COUNT(*) FILTER (WHERE first_seen_at >= :start_time AND first_seen_at < :end_time) AS jobs_created,
                COUNT(*) FILTER (WHERE availability_status = 'expired' AND last_seen_at >= :start_time AND last_seen_at < :end_time) AS jobs_expired,
                COUNT(*) FILTER (WHERE availability_status = 'active') AS jobs_active,
                COUNT(*) FILTER (WHERE is_repost = TRUE AND first_seen_at >= :start_time AND first_seen_at < :end_time) AS jobs_reposted,
                AVG(salary_min_eur) FILTER (WHERE availability_status = 'active') AS avg_salary_eur,
                percentile_cont(0.5) WITHIN GROUP (ORDER BY salary_min_eur) FILTER (WHERE availability_status = 'active') AS median_salary_eur,
                AVG(CASE WHEN remote_class IN ('remote_only', 'remote_region_locked') THEN 1.0 ELSE 0.0 END) FILTER (WHERE availability_status = 'active') AS remote_ratio
            FROM jobs
        """),
            {"start_time": start_time, "end_time": end_time},
        )
        .mappings()
        .one()
    )

    avg_job_lifetime = conn.execute(
        text(
            """
            SELECT AVG(last_seen_at - first_seen_at)
            FROM job_sources
            WHERE last_seen_at >= :start_time AND last_seen_at < :end_time
            """
        ),
        {"start_time": start_time, "end_time": end_time},
    ).scalar_one()

    return {
        "date": date,
        "jobs_created": int(jobs_stats["jobs_created"] or 0),
        "jobs_expired": int(jobs_stats["jobs_expired"] or 0),
        "jobs_active": int(jobs_stats["jobs_active"] or 0),
        "jobs_reposted": int(jobs_stats["jobs_reposted"] or 0),
        "avg_salary_eur": jobs_stats["avg_salary_eur"],
        "median_salary_eur": jobs_stats["median_salary_eur"],
        "avg_job_lifetime": avg_job_lifetime,
        "remote_ratio": jobs_stats["remote_ratio"],
    }


def get_market_daily_stats(conn: Connection, *, days: int = 30) -> list[dict]:
    """Return the last `days` rows from market_daily_stats, ordered chronologically."""
    from datetime import date, timedelta

    start_date = date.today() - timedelta(days=days)
    rows = (
        conn.execute(
            text(
                "SELECT date, jobs_created, jobs_expired, jobs_active, jobs_reposted,"
                " avg_salary_eur, median_salary_eur, remote_ratio"
                " FROM market_daily_stats"
                " WHERE date >= :start_date"
                " ORDER BY date ASC"
            ),
            {"start_date": start_date},
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def get_active_jobs_compliance_counts(conn: Connection) -> dict:
    """Return total active jobs and how many meet the feed compliance threshold (score >= 80)."""
    row = (
        conn.execute(
            text("""
                SELECT
                    COUNT(*) AS jobs_total,
                    COUNT(*) FILTER (WHERE compliance_score >= 80) AS jobs_approved
                FROM jobs
                WHERE availability_status = 'active'
            """)
        )
        .mappings()
        .one()
    )
    return {
        "jobs_total": int(row["jobs_total"] or 0),
        "jobs_approved": int(row["jobs_approved"] or 0),
    }


def backfill_remote_ratio(conn: Connection) -> int:
    """
    One-time fix: rewrite remote_ratio in all existing market_daily_stats rows
    using the new definition (remote_class IN ('REMOTE_ONLY', 'REMOTE_REGION_LOCKED')).

    Because the jobs table only holds current state (not historical snapshots),
    every row gets the same current-snapshot value — not perfectly historical,
    but eliminates the 1.0 artefact from the old `remote_scope IS NOT NULL` formula.

    Returns the number of rows updated.
    """
    result = conn.execute(
        text("""
            UPDATE market_daily_stats
            SET remote_ratio = (
                SELECT AVG(CASE WHEN remote_class IN ('remote_only', 'remote_region_locked') THEN 1.0 ELSE 0.0 END)
                FROM jobs
                WHERE availability_status = 'active'
            )
            WHERE remote_ratio IS NOT DISTINCT FROM 0.0
        """)
    )
    return result.rowcount


def insert_market_daily_stats(conn: Connection, stats: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO market_daily_stats (
                date,
                jobs_created,
                jobs_expired,
                jobs_active,
                jobs_reposted,
                avg_salary_eur,
                median_salary_eur,
                avg_job_lifetime,
                remote_ratio
            )
            VALUES (
                :date,
                :jobs_created,
                :jobs_expired,
                :jobs_active,
                :jobs_reposted,
                :avg_salary_eur,
                :median_salary_eur,
                :avg_job_lifetime,
                :remote_ratio
            )
            ON CONFLICT (date) DO NOTHING
            """
        ),
        stats,
    )
