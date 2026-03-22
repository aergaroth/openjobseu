from sqlalchemy import text
from storage.db_engine import get_engine

engine = get_engine()


def _build_jobs_audit_filter_clauses(
    *,
    status: str | None = None,
    source: str | None = None,
    company: str | None = None,
    title: str | None = None,
    remote_scope: str | None = None,
    remote_class: str | None = None,
    geo_class: str | None = None,
    compliance_status: str | None = None,
    min_compliance_score: int | None = None,
    max_compliance_score: int | None = None,
) -> tuple[list[str], dict]:
    clauses: list[str] = []
    params: dict = {}
    param_counter = 0

    if status:
        param_counter += 1
        clauses.append(f"status = :p{param_counter}")
        params[f"p{param_counter}"] = status

    if source:
        param_counter += 1
        clauses.append(
            "EXISTS ("
            "SELECT 1 FROM job_sources js_filter "
            f"WHERE js_filter.job_id = jobs.job_id AND js_filter.source = :p{param_counter}"
            ")"
        )
        params[f"p{param_counter}"] = source

    if company:
        param_counter += 1
        clauses.append(f"company_name ILIKE :p{param_counter}")
        params[f"p{param_counter}"] = f"%{company}%"

    if title:
        param_counter += 1
        clauses.append(f"title ILIKE :p{param_counter}")
        params[f"p{param_counter}"] = f"%{title}%"

    if remote_scope:
        param_counter += 1
        clauses.append(f"remote_scope ILIKE :p{param_counter}")
        params[f"p{param_counter}"] = f"%{remote_scope}%"

    if remote_class:
        param_counter += 1
        clauses.append(f"remote_class = :p{param_counter}")
        params[f"p{param_counter}"] = remote_class

    if geo_class:
        param_counter += 1
        clauses.append(f"geo_class = :p{param_counter}")
        params[f"p{param_counter}"] = geo_class

    if compliance_status:
        param_counter += 1
        clauses.append(f"compliance_status = :p{param_counter}")
        params[f"p{param_counter}"] = compliance_status

    if min_compliance_score is not None:
        param_counter += 1
        clauses.append(f"COALESCE(compliance_score, 0) >= :p{param_counter}")
        params[f"p{param_counter}"] = int(min_compliance_score)

    if max_compliance_score is not None:
        param_counter += 1
        clauses.append(f"COALESCE(compliance_score, 0) <= :p{param_counter}")
        params[f"p{param_counter}"] = int(max_compliance_score)

    return clauses, params


def _rows_to_count_map(rows: list) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        key = str(row["label"])
        result[key] = int(row["count"])
    return result


def get_jobs_audit(
    *,
    status: str | None = None,
    source: str | None = None,
    company: str | None = None,
    title: str | None = None,
    remote_scope: str | None = None,
    remote_class: str | None = None,
    geo_class: str | None = None,
    compliance_status: str | None = None,
    min_compliance_score: int | None = None,
    max_compliance_score: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    clauses, params = _build_jobs_audit_filter_clauses(
        status=status,
        source=source,
        company=company,
        title=title,
        remote_scope=remote_scope,
        remote_class=remote_class,
        geo_class=geo_class,
        compliance_status=compliance_status,
        min_compliance_score=min_compliance_score,
        max_compliance_score=max_compliance_score,
    )

    where_clause = ""
    if clauses:
        where_clause = "WHERE " + " AND ".join(clauses)

    with engine.connect() as conn:
        # Prepare params for queries
        query_params = {**params, "limit": limit, "offset": offset}

        jobs_rows = (
            conn.execute(
                text(f"""
                SELECT
                    job_id,
                    source,
                    source_url,
                    title,
                    company_name,
                    remote_scope,
                    status,
                    remote_class,
                    geo_class,
                    compliance_status,
                    compliance_score,
                    first_seen_at,
                    last_seen_at
                FROM jobs
                {where_clause}
                ORDER BY COALESCE(last_seen_at, '1970-01-01T00:00:00+00:00') DESC
                LIMIT :limit OFFSET :offset
            """),
                query_params,
            )
            .mappings()
            .all()
        )

        if not where_clause:
            total_query = "SELECT GREATEST(0, CAST(reltuples AS BIGINT)) AS total FROM pg_class c JOIN pg_namespace n ON c.relnamespace = n.oid WHERE n.nspname = 'public' AND c.relname = 'jobs'"
        else:
            total_query = f"SELECT COUNT(*) AS total FROM jobs {where_clause}"

        total_row = conn.execute(
            text(total_query),
            params,
        ).fetchone()

        status_rows = (
            conn.execute(
                text(f"""
                SELECT COALESCE(status, 'null') AS label, COUNT(*) AS count
                FROM jobs
                {where_clause}
                GROUP BY COALESCE(status, 'null')
                ORDER BY count DESC, label ASC
            """),
                params,
            )
            .mappings()
            .all()
        )

        source_rows = (
            conn.execute(
                text(f"""
                SELECT
                    COALESCE(js.source, 'null') AS label,
                    COUNT(DISTINCT jobs.job_id) AS count
                FROM jobs
                LEFT JOIN job_sources js
                    ON js.job_id = jobs.job_id
                {where_clause}
                GROUP BY COALESCE(js.source, 'null')
                ORDER BY count DESC, label ASC
            """),
                params,
            )
            .mappings()
            .all()
        )

        compliance_rows = (
            conn.execute(
                text(f"""
                SELECT COALESCE(compliance_status, 'null') AS label, COUNT(*) AS count
                FROM jobs
                {where_clause}
                GROUP BY COALESCE(compliance_status, 'null')
                ORDER BY count DESC, label ASC
            """),
                params,
            )
            .mappings()
            .all()
        )

        remote_class_rows = (
            conn.execute(
                text(f"""
                SELECT COALESCE(remote_class, 'null') AS label, COUNT(*) AS count
                FROM jobs
                {where_clause}
                GROUP BY COALESCE(remote_class, 'null')
                ORDER BY count DESC, label ASC
            """),
                params,
            )
            .mappings()
            .all()
        )

        geo_class_rows = (
            conn.execute(
                text(f"""
                SELECT COALESCE(geo_class, 'null') AS label, COUNT(*) AS count
                FROM jobs
                {where_clause}
                GROUP BY COALESCE(geo_class, 'null')
                ORDER BY count DESC, label ASC
            """),
                params,
            )
            .mappings()
            .all()
        )

    return {
        "total": int(total_row[0]) if total_row else 0,
        "limit": int(limit),
        "offset": int(offset),
        "items": [dict(row) for row in jobs_rows],
        "counts": {
            "status": _rows_to_count_map(status_rows),
            "source": _rows_to_count_map(source_rows),
            "compliance_status": _rows_to_count_map(compliance_rows),
            "remote_class": _rows_to_count_map(remote_class_rows),
            "geo_class": _rows_to_count_map(geo_class_rows),
        },
    }


def get_compliance_stats_last_7d() -> dict:
    with engine.connect() as conn:
        row = (
            conn.execute(
                text("""
                SELECT
                    COUNT(*) AS total_jobs,
                    COUNT(*) FILTER (WHERE compliance_status = 'approved') AS approved,
                    COUNT(*) FILTER (WHERE compliance_status = 'review') AS review,
                    COUNT(*) FILTER (WHERE compliance_status = 'rejected') AS rejected,
                    ROUND(
                        COUNT(*) FILTER (WHERE compliance_status = 'approved')::numeric
                        / NULLIF(COUNT(*), 0) * 100,
                        2
                    ) AS approved_ratio_pct
                FROM jobs
                WHERE first_seen_at > NOW() - INTERVAL '7 days'
            """)
            )
            .mappings()
            .one()
        )

    ratio = row["approved_ratio_pct"]
    return {
        "window": "last_7_days",
        "total_jobs": int(row["total_jobs"] or 0),
        "approved": int(row["approved"] or 0),
        "review": int(row["review"] or 0),
        "rejected": int(row["rejected"] or 0),
        "approved_ratio_pct": float(ratio) if ratio is not None else None,
    }


def get_audit_source_filter_values() -> list[str]:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT
                    js.source,
                    COUNT(*) AS count
                FROM job_sources js
                WHERE js.source IS NOT NULL
                  AND btrim(js.source) <> ''
                GROUP BY js.source
                ORDER BY count DESC, js.source ASC
            """)
            )
            .mappings()
            .all()
        )

    return [str(row["source"]) for row in rows]


def get_audit_company_compliance_stats(
    *,
    min_total_jobs: int = 10,
) -> list[dict]:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT
                    c.legal_name,
                    COUNT(*) AS total_jobs,
                    COUNT(*) FILTER (WHERE j.compliance_status = 'approved') AS approved,
                    COUNT(*) FILTER (WHERE j.compliance_status = 'rejected') AS rejected,
                    ROUND(
                        COUNT(*) FILTER (WHERE j.compliance_status = 'approved')::numeric
                        / NULLIF(COUNT(*), 0) * 100,
                        2
                    ) AS approved_ratio_pct
                FROM jobs j
                JOIN companies c ON c.company_id = j.company_id
                GROUP BY c.legal_name
                HAVING COUNT(*) > :min_total_jobs
                ORDER BY approved DESC, c.legal_name ASC
            """),
                {"min_total_jobs": int(min_total_jobs)},
            )
            .mappings()
            .all()
        )

    result: list[dict] = []
    for row in rows:
        ratio = row["approved_ratio_pct"]
        result.append(
            {
                "legal_name": str(row["legal_name"]),
                "total_jobs": int(row["total_jobs"] or 0),
                "approved": int(row["approved"] or 0),
                "rejected": int(row["rejected"] or 0),
                "approved_ratio_pct": float(ratio) if ratio is not None else None,
            }
        )
    return result


def get_audit_source_compliance_stats_last_7d() -> list[dict]:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT
                    js.source AS source,
                    COUNT(DISTINCT j.job_id) AS total_jobs,
                    COUNT(DISTINCT j.job_id) FILTER (WHERE j.compliance_status = 'approved') AS approved,
                    COUNT(DISTINCT j.job_id) FILTER (WHERE j.compliance_status = 'rejected') AS rejected,
                    ROUND(
                        COUNT(DISTINCT j.job_id) FILTER (WHERE j.compliance_status = 'approved')::numeric
                        / NULLIF(COUNT(DISTINCT j.job_id), 0) * 100,
                        2
                    ) AS approved_ratio_pct
                FROM jobs j
                JOIN job_sources js ON js.job_id = j.job_id
                WHERE j.first_seen_at > NOW() - INTERVAL '7 days'
                GROUP BY js.source
                ORDER BY approved DESC, js.source ASC
            """)
            )
            .mappings()
            .all()
        )

    result: list[dict] = []
    for row in rows:
        ratio = row["approved_ratio_pct"]
        result.append(
            {
                "source": row["source"],
                "total_jobs": int(row["total_jobs"] or 0),
                "approved": int(row["approved"] or 0),
                "rejected": int(row["rejected"] or 0),
                "approved_ratio_pct": float(ratio) if ratio is not None else None,
            }
        )
    return result


def get_ghost_jobs(days_threshold: int = 3) -> list[dict]:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT
                    job_id,
                    source,
                    source_job_id,
                    first_seen_at,
                    last_seen_at,
                    (last_seen_at - first_seen_at) AS lifetime
                FROM job_sources
                WHERE first_seen_at > NOW() - INTERVAL '30 days'
                  AND last_seen_at - first_seen_at < (:days_threshold * INTERVAL '1 day')
            """),
                {"days_threshold": int(days_threshold)},
            )
            .mappings()
            .all()
        )

    return [dict(row) for row in rows]


def get_job_lifetime_stats() -> dict:
    with engine.connect() as conn:
        row = (
            conn.execute(
                text("""
                SELECT
                    AVG(last_seen_at - first_seen_at) AS avg_lifetime,
                    PERCENTILE_CONT(0.5)
                    WITHIN GROUP (ORDER BY last_seen_at - first_seen_at)
                    AS median_lifetime
                FROM job_sources
                    WHERE first_seen_at > NOW() - INTERVAL '30 days'
            """)
            )
            .mappings()
            .one()
        )

    return {
        "avg_lifetime": row["avg_lifetime"],
        "median_lifetime": row["median_lifetime"],
    }


def get_repost_candidates(days_threshold: int = 30) -> list[dict]:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT
                    j.job_id,
                    j.company_name,
                    j.title,
                    j.first_seen_at,
                    prev.last_seen_at AS previous_last_seen_at,
                    (j.first_seen_at - prev.last_seen_at) AS gap
                FROM jobs j
                JOIN jobs prev
                  ON j.job_fingerprint = prev.job_fingerprint
                 AND j.company_name = prev.company_name
                 AND j.title = prev.title
                 AND j.job_id <> prev.job_id
                WHERE j.first_seen_at > NOW() - ((:days_threshold + 15) * INTERVAL '1 day')
                  AND j.first_seen_at > prev.last_seen_at
                  AND j.first_seen_at - prev.last_seen_at < (:days_threshold * INTERVAL '1 day')
                ORDER BY j.first_seen_at DESC
            """),
                {"days_threshold": int(days_threshold)},
            )
            .mappings()
            .all()
        )

    return [dict(row) for row in rows]


def get_failing_ats_integrations(days_threshold: int = 3) -> list[dict]:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT
                    ca.company_ats_id,
                    c.legal_name,
                    ca.provider,
                    ca.ats_slug,
                    ca.careers_url,
                    ca.last_sync_at,
                    ca.created_at
                FROM company_ats ca
                JOIN companies c ON c.company_id = ca.company_id
                WHERE ca.is_active = TRUE
                  AND c.is_active = TRUE
                  AND (
                      ca.last_sync_at < NOW() - (:days_threshold * INTERVAL '1 day')
                      OR (ca.last_sync_at IS NULL AND ca.created_at < NOW() - (:days_threshold * INTERVAL '1 day'))
                  )
                ORDER BY COALESCE(ca.last_sync_at, ca.created_at) ASC
            """),
                {"days_threshold": int(days_threshold)},
            )
            .mappings()
            .all()
        )

    result = []
    for row in rows:
        d = dict(row)
        d["company_ats_id"] = str(d["company_ats_id"])
        result.append(d)
    return result
