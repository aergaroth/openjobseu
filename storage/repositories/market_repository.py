from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Connection


def compute_market_stats(conn: Connection, date: date) -> dict:
    jobs_created = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM jobs
            WHERE DATE(first_seen_at) = :date
            """
        ),
        {"date": date},
    ).scalar_one()

    jobs_expired = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM jobs
            WHERE availability_status = 'expired'
              AND DATE(last_seen_at) = :date
            """
        ),
        {"date": date},
    ).scalar_one()

    jobs_active = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM jobs
            WHERE availability_status = 'active'
            """
        )
    ).scalar_one()

    jobs_reposted = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM (
                SELECT job_fingerprint
                FROM jobs
                GROUP BY job_fingerprint
                HAVING COUNT(*) > 1
            ) t
            """
        )
    ).scalar_one()

    avg_salary_eur = conn.execute(
        text(
            """
            SELECT AVG(salary_min_eur)
            FROM jobs
            WHERE salary_min_eur IS NOT NULL
            """
        )
    ).scalar_one()

    median_salary_eur = conn.execute(
        text(
            """
            SELECT percentile_cont(0.5)
            WITHIN GROUP (ORDER BY salary_min_eur)
            FROM jobs
            WHERE salary_min_eur IS NOT NULL
            """
        )
    ).scalar_one()

    avg_job_lifetime = conn.execute(
        text(
            """
            SELECT AVG(last_seen_at - first_seen_at)
            FROM job_sources
            WHERE last_seen_at IS NOT NULL
            """
        )
    ).scalar_one()

    remote_ratio = conn.execute(
        text(
            """
            SELECT
                AVG(
                    CASE
                        WHEN remote_scope IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                )
            FROM jobs
            """
        )
    ).scalar_one()

    return {
        "date": date,
        "jobs_created": int(jobs_created or 0),
        "jobs_expired": int(jobs_expired or 0),
        "jobs_active": int(jobs_active or 0),
        "jobs_reposted": int(jobs_reposted or 0),
        "avg_salary_eur": avg_salary_eur,
        "median_salary_eur": median_salary_eur,
        "avg_job_lifetime": avg_job_lifetime,
        "remote_ratio": remote_ratio,
    }


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