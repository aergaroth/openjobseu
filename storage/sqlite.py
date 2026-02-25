''' 
this file now uses SQLAlchemy Core for database interactions, 
but retains the same function signatures and overall structure 
as before to minimize impact on other parts of the codebase. 
'''

import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Connection
from storage.db import get_engine
from app.workers.policy.v2.geo_classifier import classify_geo_scope

engine = get_engine()


def _derive_remote_class(job: dict) -> str:
    compliance = job.get("_compliance")
    if not isinstance(compliance, dict):
        return "remote_only" if bool(job.get("remote_source_flag")) else "unknown"

    policy_reason = str(compliance.get("policy_reason") or "").strip().lower()
    remote_model = str(compliance.get("remote_model") or "").strip().lower()

    if policy_reason == "non_remote":
        return "non_remote"

    mapping = {
        "remote_only": "remote_only",
        "remote_but_geo_restricted": "remote_but_geo_restricted",
        "hybrid": "non_remote",
        "office_first": "non_remote",
        "non_remote": "non_remote",
        "unknown": "unknown",
    }
    return mapping.get(remote_model, "unknown")


def _normalize_geo_class_value(value: str | None) -> str:
    geo = str(value or "").strip().lower()
    mapping = {
        "eu_member_state": "eu_member_state",
        "eu_region": "eu_region",
        "eu_explicit": "eu_explicit",
        "eog": "eu_region",
        "uk": "uk",
        "worldwide": "unknown",
        "global": "unknown",
        "eu_friendly": "unknown",
        "non_eu": "non_eu",
        "non_eu_restricted": "non_eu",
        "unknown": "unknown",
    }
    return mapping.get(geo, "unknown")


def _derive_geo_class(job: dict) -> str:
    compliance = job.get("_compliance")
    policy_reason = ""
    remote_model = ""
    explicit_geo_class = None

    if isinstance(compliance, dict):
        policy_reason = str(compliance.get("policy_reason") or "").strip().lower()
        remote_model = str(compliance.get("remote_model") or "").strip().lower()
        explicit_geo_class = compliance.get("geo_class")

    if explicit_geo_class:
        normalized = _normalize_geo_class_value(str(explicit_geo_class))
        if normalized != "unknown":
            return normalized

    if policy_reason == "geo_restriction" or remote_model == "remote_but_geo_restricted":
        return "non_eu"

    classifier_result = classify_geo_scope(
        str(job.get("title") or ""),
        str(job.get("description") or ""),
    )
    normalized_classifier_geo = _normalize_geo_class_value(
        str(classifier_result.get("geo_class") or "")
    )
    if normalized_classifier_geo != "unknown":
        return normalized_classifier_geo

    remote_scope = str(job.get("remote_scope") or "").strip()
    if remote_scope:
        remote_scope_result = classify_geo_scope(remote_scope, "")
        normalized_remote_scope_geo = _normalize_geo_class_value(
            str(remote_scope_result.get("geo_class") or "")
        )
        if normalized_remote_scope_geo != "unknown":
            return normalized_remote_scope_geo

    return "unknown"


def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                source TEXT,
                source_job_id TEXT,
                source_url TEXT,
                title TEXT,
                company_name TEXT,
                description TEXT,
                remote_source_flag BOOLEAN,
                remote_scope TEXT,
                status TEXT,
                first_seen_at TIMESTAMP WITH TIME ZONE,
                last_seen_at TIMESTAMP WITH TIME ZONE,
                last_verified_at TIMESTAMP WITH TIME ZONE,
                verification_failures INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP WITH TIME ZONE,
                remote_class TEXT,
                geo_class TEXT,
                policy_v1_decision TEXT,
                policy_v1_reason TEXT,
                policy_v2_decision TEXT,
                policy_v2_reason TEXT,
                compliance_status TEXT,
                compliance_score INTEGER
            );
        """))


def _require_open_conn(conn: Connection | None, *, op_name: str) -> Connection:
    if conn is None:
        raise ValueError(f"{op_name} requires an explicit open transaction connection (conn).")
    return conn


def _upsert_job_in_conn(
    conn: Connection,
    *,
    job: dict,
    first_seen_at,
    now,
    remote_class: str,
    geo_class: str,
) -> None:
    conn.execute(
        text("""
            INSERT INTO jobs (
                job_id,
                source,
                source_job_id,
                source_url,
                title,
                company_name,
                description,
                remote_source_flag,
                remote_scope,
                status,
                first_seen_at,
                last_seen_at,
                remote_class,
                geo_class
            )
            VALUES (
                :job_id,
                :source,
                :source_job_id,
                :source_url,
                :title,
                :company_name,
                :description,
                :remote_source_flag,
                :remote_scope,
                :status,
                :first_seen_at,
                :last_seen_at,
                :remote_class,
                :geo_class
            )
            ON CONFLICT (job_id) DO UPDATE SET
                source_url = excluded.source_url,
                title = excluded.title,
                company_name = excluded.company_name,
                description = excluded.description,
                remote_source_flag = excluded.remote_source_flag,
                remote_scope = excluded.remote_scope,
                status = excluded.status,
                remote_class = excluded.remote_class,
                geo_class = excluded.geo_class,
                first_seen_at = CASE
                    WHEN excluded.first_seen_at < jobs.first_seen_at
                    THEN excluded.first_seen_at
                    ELSE jobs.first_seen_at
                END,
                last_seen_at = excluded.last_seen_at
        """),
        {
            "job_id": job["job_id"],
            "source": job["source"],
            "source_job_id": job["source_job_id"],
            "source_url": job["source_url"],
            "title": job["title"],
            "company_name": job["company_name"],
            "description": job["description"],
            "remote_source_flag": bool(job["remote_source_flag"]),
            "remote_scope": job["remote_scope"],
            "status": job["status"],
            "first_seen_at": first_seen_at,
            "last_seen_at": now,
            "remote_class": remote_class,
            "geo_class": geo_class,
        },
    )


def upsert_job(job: dict, conn: Connection | None = None):
    now = datetime.now(timezone.utc)
    first_seen_at = job.get("first_seen_at") or now
    remote_class = _derive_remote_class(job)
    geo_class = _derive_geo_class(job)
    target_conn = _require_open_conn(conn, op_name="upsert_job")
    _upsert_job_in_conn(
        target_conn,
        job=job,
        first_seen_at=first_seen_at,
        now=now,
        remote_class=remote_class,
        geo_class=geo_class,
    )

def get_jobs_for_verification(limit: int = 20) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    job_id,
                    source_url,
                    status,
                    last_verified_at,
                    verification_failures
                FROM jobs
                WHERE status IN ('active', 'stale', 'unreachable')
                ORDER BY
                    COALESCE(last_seen_at, '1970-01-01T00:00:00+00:00')
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().all()
    return [dict(row) for row in rows]


def update_job_availability(
    job_id: str,
    status: str,
    verified_at: datetime | None = None,
    failure: bool = False,
    conn: Connection | None = None,
):
    if verified_at is None:
        verified_at = datetime.now(timezone.utc)
    update_jobs_availability(
        updates=[
            {
                "job_id": job_id,
                "status": status,
                "verified_at": verified_at,
                "failure": bool(failure),
                "updated_at": verified_at,
            }
        ],
        conn=conn,
    )


def update_jobs_availability(
    updates: list[dict],
    conn: Connection | None = None,
) -> None:
    if not updates:
        return

    normalized_updates = []
    for item in updates:
        verified_at = item.get("verified_at") or datetime.now(timezone.utc)
        normalized_updates.append(
            {
                "job_id": item["job_id"],
                "status": item["status"],
                "verified_at": verified_at,
                "failure": bool(item.get("failure", False)),
                "updated_at": item.get("updated_at") or verified_at,
            }
        )

    target_conn = _require_open_conn(conn, op_name="update_jobs_availability")
    target_conn.execute(
        text("""
            UPDATE jobs
            SET
                status = :status,
                last_verified_at = :verified_at,
                verification_failures = CASE
                    WHEN :failure THEN verification_failures + 1
                    ELSE 0
                END,
                updated_at = :updated_at
            WHERE job_id = :job_id
        """),
        normalized_updates,
    )


def count_jobs_missing_compliance() -> int:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT COUNT(*) AS count
                FROM jobs
                WHERE compliance_status IS NULL OR compliance_score IS NULL
            """)
        ).fetchone()
    return int(row[0]) if row else 0


def backfill_missing_compliance_classes(limit: int = 1000) -> int:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    job_id,
                    title,
                    description,
                    remote_source_flag,
                    remote_scope,
                    policy_v1_reason,
                    remote_class,
                    geo_class
                FROM jobs
                WHERE remote_class IS NULL OR geo_class IS NULL
                ORDER BY COALESCE(last_seen_at, '1970-01-01T00:00:00+00:00') DESC
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().all()

    if not rows:
        return 0

    now = datetime.now(timezone.utc)

    payloads: list[dict] = []
    for row in rows:
        payload = dict(row)
        if payload.get("policy_v1_reason"):
            payload["_compliance"] = {
                "policy_reason": payload["policy_v1_reason"],
                "remote_model": "unknown",
            }

        remote_class = payload.get("remote_class") or _derive_remote_class(payload)
        geo_class = payload.get("geo_class") or _derive_geo_class(payload)
        payloads.append(
            {
                "remote_class": remote_class,
                "geo_class": geo_class,
                "updated_at": now,
                "job_id": payload["job_id"],
            }
        )

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE jobs
                SET
                    remote_class = :remote_class,
                    geo_class = :geo_class,
                    updated_at = :updated_at
                WHERE job_id = :job_id
            """),
            payloads,
        )

    return len(rows)


def get_jobs_for_compliance_resolution(
    limit: int = 500,
    only_missing: bool = False,
) -> list[dict]:
    where_clause = ""
    if only_missing:
        where_clause = "WHERE compliance_status IS NULL OR compliance_score IS NULL"

    query = f"""
        SELECT
            job_id,
            remote_class,
            geo_class
        FROM jobs
        {where_clause}
        ORDER BY COALESCE(last_seen_at, '1970-01-01T00:00:00+00:00') DESC
        LIMIT :limit
    """

    with engine.connect() as conn:
        rows = conn.execute(
            text(query),
            {"limit": limit},
        ).mappings().all()
    
    return [dict(row) for row in rows]


def update_job_compliance_resolution(
    job_id: str,
    compliance_status: str,
    compliance_score: int,
    conn: Connection | None = None,
):
    now = datetime.now(timezone.utc)
    update_jobs_compliance_resolution(
        updates=[
            {
                "job_id": job_id,
                "compliance_status": compliance_status,
                "compliance_score": int(compliance_score),
                "updated_at": now,
            }
        ],
        conn=conn,
    )


def update_jobs_compliance_resolution(
    updates: list[dict],
    conn: Connection | None = None,
) -> None:
    if not updates:
        return

    now = datetime.now(timezone.utc)
    normalized_updates = [
        {
            "job_id": item["job_id"],
            "compliance_status": item["compliance_status"],
            "compliance_score": int(item["compliance_score"]),
            "updated_at": item.get("updated_at") or now,
        }
        for item in updates
    ]

    target_conn = _require_open_conn(conn, op_name="update_jobs_compliance_resolution")
    target_conn.execute(
        text("""
            UPDATE jobs
            SET
                compliance_status = :compliance_status,
                compliance_score = :compliance_score,
                updated_at = :updated_at
            WHERE job_id = :job_id
        """),
        normalized_updates,
    )


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
        clauses.append(f"source = :p{param_counter}")
        params[f"p{param_counter}"] = source

    if company:
        param_counter += 1
        clauses.append(f"LOWER(company_name) LIKE :p{param_counter}")
        params[f"p{param_counter}"] = f"%{company.lower()}%"

    if title:
        param_counter += 1
        clauses.append(f"LOWER(title) LIKE :p{param_counter}")
        params[f"p{param_counter}"] = f"%{title.lower()}%"

    if remote_scope:
        param_counter += 1
        clauses.append(f"LOWER(remote_scope) LIKE :p{param_counter}")
        params[f"p{param_counter}"] = f"%{remote_scope.lower()}%"

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
        
        jobs_rows = conn.execute(
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
        ).mappings().all()

        total_row = conn.execute(
            text(f"""
                SELECT COUNT(*) AS total
                FROM jobs
                {where_clause}
            """),
            params,
        ).fetchone()

        status_rows = conn.execute(
            text(f"""
                SELECT COALESCE(status, 'null') AS label, COUNT(*) AS count
                FROM jobs
                {where_clause}
                GROUP BY COALESCE(status, 'null')
                ORDER BY count DESC, label ASC
            """),
            params,
        ).mappings().all()

        source_rows = conn.execute(
            text(f"""
                SELECT COALESCE(source, 'null') AS label, COUNT(*) AS count
                FROM jobs
                {where_clause}
                GROUP BY COALESCE(source, 'null')
                ORDER BY count DESC, label ASC
            """),
            params,
        ).mappings().all()

        compliance_rows = conn.execute(
            text(f"""
                SELECT COALESCE(compliance_status, 'null') AS label, COUNT(*) AS count
                FROM jobs
                {where_clause}
                GROUP BY COALESCE(compliance_status, 'null')
                ORDER BY count DESC, label ASC
            """),
            params,
        ).mappings().all()

        remote_class_rows = conn.execute(
            text(f"""
                SELECT COALESCE(remote_class, 'null') AS label, COUNT(*) AS count
                FROM jobs
                {where_clause}
                GROUP BY COALESCE(remote_class, 'null')
                ORDER BY count DESC, label ASC
            """),
            params,
        ).mappings().all()

        geo_class_rows = conn.execute(
            text(f"""
                SELECT COALESCE(geo_class, 'null') AS label, COUNT(*) AS count
                FROM jobs
                {where_clause}
                GROUP BY COALESCE(geo_class, 'null')
                ORDER BY count DESC, label ASC
            """),
            params,
        ).mappings().all()

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


def get_jobs(
    status: str | None = None,
    company: str | None = None,
    title: str | None = None,
    source: str | None = None,
    remote_scope: str | None = None,
    min_compliance_score: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    clauses = []
    params = {}
    param_counter = 0

    if status == "visible":
        clauses.append("status IN ('new', 'active')")
    elif status:
        param_counter += 1
        clauses.append(f"status = :p{param_counter}")
        params[f"p{param_counter}"] = status

    if company:
        param_counter += 1
        clauses.append(f"LOWER(company_name) LIKE :p{param_counter}")
        params[f"p{param_counter}"] = f"%{company.lower()}%"

    if title:
        param_counter += 1
        clauses.append(f"LOWER(title) LIKE :p{param_counter}")
        params[f"p{param_counter}"] = f"%{title.lower()}%"

    if source:
        param_counter += 1
        clauses.append(f"source = :p{param_counter}")
        params[f"p{param_counter}"] = source

    if remote_scope:
        param_counter += 1
        clauses.append(f"remote_scope = :p{param_counter}")
        params[f"p{param_counter}"] = remote_scope

    if min_compliance_score is not None:
        param_counter += 1
        clauses.append(f"COALESCE(compliance_score, 0) >= :p{param_counter}")
        params[f"p{param_counter}"] = int(min_compliance_score)

    where_clause = ""
    if clauses:
        where_clause = "WHERE " + " AND ".join(clauses)

    query = f"""
        SELECT
            job_id,
            source,
            source_url,
            title,
            company_name,
            remote_scope,
            status,
            first_seen_at,
            last_seen_at
        FROM jobs
        {where_clause}
        ORDER BY first_seen_at DESC
        LIMIT :limit OFFSET :offset
    """

    params["limit"] = limit
    params["offset"] = offset

    with engine.connect() as conn:
        rows = conn.execute(
            text(query),
            params,
        ).mappings().all()

    return [dict(row) for row in rows]
