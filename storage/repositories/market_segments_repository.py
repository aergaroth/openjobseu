from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection


def compute_market_segments(conn: Connection, date: date) -> list[dict]:
    start_time = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    end_time = start_time + timedelta(days=1)

    rows: list[dict] = []

    # Country segment: group EU jobs by remote_scope, aggregate all non-EU into "Non EU"
    country_result = conn.execute(
        text("""
            SELECT
                CASE
                    WHEN geo_class IN ('eu_member_state', 'eu_explicit', 'eu_region')
                        THEN COALESCE(remote_scope, geo_class)
                    ELSE 'Non EU'
                END AS segment_value,
                COUNT(*) FILTER (WHERE availability_status = 'active') AS jobs_active,
                COUNT(*) FILTER (WHERE first_seen_at >= :start_time AND first_seen_at < :end_time) AS jobs_created,
                AVG(salary_min_eur) AS avg_salary_eur,
                percentile_cont(0.5)
                    WITHIN GROUP (ORDER BY salary_min_eur) AS median_salary_eur
            FROM jobs
            WHERE geo_class IS NOT NULL
              AND compliance_status = 'approved'
              AND (availability_status = 'active'
                   OR (first_seen_at >= :start_time AND first_seen_at < :end_time))
            GROUP BY segment_value
        """),
        {"start_time": start_time, "end_time": end_time},
    )

    for item in country_result.mappings():
        rows.append(
            {
                "date": date,
                "segment_type": "country",
                "segment_value": item["segment_value"],
                "jobs_active": int(item["jobs_active"] or 0),
                "jobs_created": int(item["jobs_created"] or 0),
                "avg_salary_eur": item["avg_salary_eur"],
                "median_salary_eur": item["median_salary_eur"],
            }
        )

    # job_family and seniority segments: filter to approved offers only
    for segment_type, column_name in [("job_family", "job_family"), ("seniority", "seniority")]:
        result = conn.execute(
            text(
                f"""
                SELECT
                    {column_name} AS segment_value,
                    COUNT(*) FILTER (WHERE availability_status = 'active') AS jobs_active,
                    COUNT(*) FILTER (WHERE first_seen_at >= :start_time AND first_seen_at < :end_time) AS jobs_created,
                    AVG(salary_min_eur) AS avg_salary_eur,
                    percentile_cont(0.5)
                        WITHIN GROUP (ORDER BY salary_min_eur) AS median_salary_eur
                FROM jobs
                WHERE {column_name} IS NOT NULL
                  AND compliance_status = 'approved'
                  AND (availability_status = 'active'
                       OR (first_seen_at >= :start_time AND first_seen_at < :end_time))
                GROUP BY {column_name}
                """
            ),
            {"start_time": start_time, "end_time": end_time},
        )

        for item in result.mappings():
            rows.append(
                {
                    "date": date,
                    "segment_type": segment_type,
                    "segment_value": item["segment_value"],
                    "jobs_active": int(item["jobs_active"] or 0),
                    "jobs_created": int(item["jobs_created"] or 0),
                    "avg_salary_eur": item["avg_salary_eur"],
                    "median_salary_eur": item["median_salary_eur"],
                }
            )

    return rows


def get_market_segments_snapshot(conn: Connection) -> list[dict]:
    """Return the most recent day's segment rows from market_daily_stats_segments.

    Returns all segment_type/segment_value pairs for the latest available date,
    ordered by segment_type and jobs_active descending.
    """
    rows = (
        conn.execute(
            text("""
                SELECT segment_type, segment_value, jobs_active, jobs_created,
                       avg_salary_eur, median_salary_eur
                FROM market_daily_stats_segments
                WHERE date = (SELECT MAX(date) FROM market_daily_stats_segments)
                ORDER BY segment_type, jobs_active DESC
            """)
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def insert_market_segments(conn: Connection, rows: list[dict]) -> None:
    if not rows:
        return

    conn.execute(
        text(
            """
            INSERT INTO market_daily_stats_segments (
                date,
                segment_type,
                segment_value,
                jobs_active,
                jobs_created,
                avg_salary_eur,
                median_salary_eur
            )
            VALUES (
                :date,
                :segment_type,
                :segment_value,
                :jobs_active,
                :jobs_created,
                :avg_salary_eur,
                :median_salary_eur
            )
            ON CONFLICT (date, segment_type, segment_value)
            DO NOTHING
            """
        ),
        rows,
    )
