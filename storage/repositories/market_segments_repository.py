import re as _re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection

_EXCLUDE_SCOPE_KEYWORDS = ["americ", "apac", "latam", "asia pacific"]


def _canonical_region(val: str) -> str:
    """Strip remote markers and formal country name prefixes to get the base region name."""
    val = _re.sub(r"(?i)^republic\s+of\s+", "", val)
    val = _re.sub(r"(?i)^remote\s*[-–]\s*", "", val)
    val = _re.sub(r"(?i)\s*\(remote\)\s*$", "", val)
    return val.strip()


def _remote_priority(val: str) -> int:
    """Lower = preferred. 'Remote - X' > 'X (Remote)' > plain 'X'."""
    if _re.match(r"(?i)^remote\s*[-–]", val):
        return 0
    if val.lower().endswith(" (remote)"):
        return 1
    return 2


def _normalize_country_rows(rows: list[dict]) -> list[dict]:
    normalized = []
    for row in rows:
        val = row["segment_value"] or ""
        if any(kw in val.lower() for kw in _EXCLUDE_SCOPE_KEYWORDS):
            continue
        val = _re.sub(r"(?i)^home\s+based\s*[-–]\s*", "Remote - ", val)
        # "Remote Job, Warsaw" → "Remote - Warsaw"
        val = _re.sub(r"(?i)^remote\s+job\s*[,\s]+\s*", "Remote - ", val)
        # "Sweden (Remote)" → "Remote - Sweden"
        val = _re.sub(r"(?i)^(.+?)\s*\(remote\)\s*$", r"Remote - \1", val)
        normalized.append({**row, "segment_value": val})

    # For each canonical region, keep only the highest-priority label.
    # e.g. "Remote - EMEA" wins over "EMEA"; "Spain (Remote)" wins over "Spain".
    canonical_to_best: dict[str, str] = {}
    for r in normalized:
        v = r["segment_value"]
        c = _canonical_region(v)
        if not c:
            continue
        if c not in canonical_to_best or _remote_priority(v) < _remote_priority(canonical_to_best[c]):
            canonical_to_best[c] = v

    best_labels = set(canonical_to_best.values())
    return [r for r in normalized if r["segment_value"] in best_labels]


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
                COUNT(*) FILTER (WHERE salary_min_eur >= 10000) AS salary_count,
                AVG(CASE WHEN salary_min_eur >= 10000 THEN salary_min_eur END) AS avg_salary_eur,
                percentile_cont(0.5)
                    WITHIN GROUP (ORDER BY CASE WHEN salary_min_eur >= 10000 THEN salary_min_eur END) AS median_salary_eur
            FROM jobs
            WHERE geo_class IS NOT NULL
              AND compliance_status = 'approved'
              AND compliance_score >= 80
              AND (availability_status = 'active'
                   OR (first_seen_at >= :start_time AND first_seen_at < :end_time))
            GROUP BY segment_value
        """),
        {"start_time": start_time, "end_time": end_time},
    )

    country_rows = []
    for item in country_result.mappings():
        country_rows.append(
            {
                "date": date,
                "segment_type": "country",
                "segment_value": item["segment_value"],
                "jobs_active": int(item["jobs_active"] or 0),
                "jobs_created": int(item["jobs_created"] or 0),
                "salary_count": int(item["salary_count"] or 0),
                "avg_salary_eur": item["avg_salary_eur"],
                "median_salary_eur": item["median_salary_eur"],
            }
        )
    rows.extend(_normalize_country_rows(country_rows))

    # job_family and seniority segments: filter to approved offers only
    for segment_type, column_name in [("job_family", "job_family"), ("seniority", "seniority")]:
        result = conn.execute(
            text(
                f"""
                SELECT
                    {column_name} AS segment_value,
                    COUNT(*) FILTER (WHERE availability_status = 'active') AS jobs_active,
                    COUNT(*) FILTER (WHERE first_seen_at >= :start_time AND first_seen_at < :end_time) AS jobs_created,
                    COUNT(*) FILTER (WHERE salary_min_eur >= 10000) AS salary_count,
                    AVG(CASE WHEN salary_min_eur >= 10000 THEN salary_min_eur END) AS avg_salary_eur,
                    percentile_cont(0.5)
                        WITHIN GROUP (ORDER BY CASE WHEN salary_min_eur >= 10000 THEN salary_min_eur END) AS median_salary_eur
                FROM jobs
                WHERE {column_name} IS NOT NULL
                  AND compliance_status = 'approved'
                  AND compliance_score >= 80
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
                    "salary_count": int(item["salary_count"] or 0),
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
                       salary_count, avg_salary_eur, median_salary_eur
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
                salary_count,
                avg_salary_eur,
                median_salary_eur
            )
            VALUES (
                :date,
                :segment_type,
                :segment_value,
                :jobs_active,
                :jobs_created,
                :salary_count,
                :avg_salary_eur,
                :median_salary_eur
            )
            ON CONFLICT (date, segment_type, segment_value)
            DO UPDATE SET
                jobs_active = EXCLUDED.jobs_active,
                jobs_created = EXCLUDED.jobs_created,
                salary_count = EXCLUDED.salary_count,
                avg_salary_eur = EXCLUDED.avg_salary_eur,
                median_salary_eur = EXCLUDED.median_salary_eur
            """
        ),
        rows,
    )
