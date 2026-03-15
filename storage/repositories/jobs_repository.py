import logging
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Connection
from storage.db_engine import get_engine
from storage.common import _derive_source_fields, _require_open_conn
from app.domain.jobs.identity import compute_job_fingerprint, compute_job_uid
from app.domain.jobs.canonical_identity import compute_canonical_job_id
from app.domain.money.salary_parser import extract_salary

logger = logging.getLogger(__name__)

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
        clauses.append(
            "EXISTS ("
            "SELECT 1 FROM job_sources js_filter "
            f"WHERE js_filter.job_id = jobs.job_id AND js_filter.source = :p{param_counter}"
            ")"
        )
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

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(query),
            params,
        ).mappings().all()

    return [dict(row) for row in rows]

def _find_job_id_by_source_mapping(
    conn: Connection, *, source: str, source_job_id: str
) -> str | None:
    row = conn.execute(
        text("""
            SELECT job_id
            FROM job_sources
            WHERE source = :source
              AND source_job_id = :source_job_id
            LIMIT 1
        """),
        {"source": source, "source_job_id": source_job_id},
    ).fetchone()
    if row and row[0]:
        return str(row[0])

    # Backward-compatible fallback while old rows are being backfilled.
    legacy_row = conn.execute(
        text("""
            SELECT job_id
            FROM jobs
            WHERE source = :source
              AND source_job_id = :source_job_id
            LIMIT 1
        """),
        {"source": source, "source_job_id": source_job_id},
    ).fetchone()
    if legacy_row and legacy_row[0]:
        return str(legacy_row[0])

    return None

def _find_job_id_by_fingerprint(conn: Connection, *, job_fingerprint: str) -> str | None:
    row = conn.execute(
        text("""
            SELECT job_id
            FROM jobs
            WHERE job_fingerprint = :job_fingerprint
            LIMIT 1
        """),
        {"job_fingerprint": job_fingerprint},
    ).fetchone()
    if row and row[0]:
        return str(row[0])
    return None

def _job_exists(conn: Connection, *, job_id: str) -> bool:
    row = conn.execute(
        text("""
            SELECT 1
            FROM jobs
            WHERE job_id = :job_id
            LIMIT 1
        """),
        {"job_id": job_id},
    ).fetchone()
    return bool(row)

def _resolve_canonical_job_id(
    conn: Connection,
    *,
    incoming_job_id: str,
    source: str,
    source_job_id: str,
    job_fingerprint: str,
) -> str:
    by_fingerprint = _find_job_id_by_fingerprint(
        conn,
        job_fingerprint=job_fingerprint,
    )
    if by_fingerprint:
        return by_fingerprint

    by_source_mapping = _find_job_id_by_source_mapping(
        conn,
        source=source,
        source_job_id=source_job_id,
    )
    if by_source_mapping:
        return by_source_mapping

    if _job_exists(conn, job_id=incoming_job_id):
        return incoming_job_id

    return incoming_job_id

def _upsert_job_source_mapping_in_conn(
    conn: Connection,
    *,
    job_id: str,
    source: str,
    source_job_id: str,
    source_url: str | None,
    first_seen_at,
    now,
) -> None:
    conn.execute(
        text("""
            INSERT INTO job_sources (
                job_id,
                source,
                source_job_id,
                source_url,
                first_seen_at,
                last_seen_at,
                created_at,
                updated_at
            )
            VALUES (
                :job_id,
                :source,
                :source_job_id,
                :source_url,
                :first_seen_at,
                :last_seen_at,
                :created_at,
                :updated_at
            )
            ON CONFLICT (source, source_job_id) DO UPDATE SET
                job_id = excluded.job_id,
                source_url = excluded.source_url,
                first_seen_at = CASE
                    WHEN excluded.first_seen_at < job_sources.first_seen_at
                    THEN excluded.first_seen_at
                    ELSE job_sources.first_seen_at
                END,
                last_seen_at = excluded.last_seen_at,
                seen_count = job_sources.seen_count + 1,
                updated_at = excluded.updated_at
        """),
        {
            "job_id": job_id,
            "source": source,
            "source_job_id": source_job_id,
            "source_url": source_url,
            "first_seen_at": first_seen_at,
            "last_seen_at": now,
            "created_at": now,
            "updated_at": now,
        },
    )

def _insert_job_snapshot_in_conn(conn: Connection, job: dict) -> None:
    conn.execute(
        text("""
            INSERT INTO job_snapshots (
                job_id,
                job_fingerprint,
                title,
                company_name,
                salary_min,
                salary_max,
                salary_currency,
                remote_class,
                geo_class
            )
            VALUES (
                :job_id,
                :job_fingerprint,
                :title,
                :company_name,
                :salary_min,
                :salary_max,
                :salary_currency,
                :remote_class,
                :geo_class
            )
        """),
        job,
    )

def _upsert_job_in_conn(
    conn: Connection,
    *,
    job: dict,
    first_seen_at,
    now,
    company_id: str | None = None,
) -> str:
    resolved_source, resolved_source_job_id, resolved_source_url = _derive_source_fields(job)

    # Fallback to compute identity if missing (happens in many tests)
    if "job_fingerprint" not in job:
        job["job_fingerprint"] = compute_job_fingerprint(
            job.get("description") or "",
            title=job.get("title") or "",
            location=job.get("remote_scope"),
            company_id=job.get("company_id") or company_id,
            company_name=job.get("company_name") or "",
        )
    if "job_uid" not in job:
        job["job_uid"] = compute_job_uid(
            company_id=job.get("company_id") or company_id,
            title=job.get("title") or "",
            location=job.get("remote_scope"),
        )

    # Fallback for salary extraction (happens in some tests)
    if job.get("salary_min") is None and job.get("salary_max") is None:
        salary_info = extract_salary(job.get("description") or "", title=job.get("title"))
        if salary_info:
            job.update(salary_info)

    canonical_job_id = _resolve_canonical_job_id(
        conn,
        incoming_job_id=str(job["job_id"]),
        source=resolved_source,
        source_job_id=resolved_source_job_id,
        job_fingerprint=str(job["job_fingerprint"]),
    )

    # Detect fingerprint change and snapshot previous state
    existing_job = conn.execute(
        text("""
            SELECT
                job_fingerprint,
                title,
                company_name,
                salary_min,
                salary_max,
                salary_currency,
                remote_class,
                geo_class
            FROM jobs
            WHERE job_id = :job_id
        """),
        {"job_id": canonical_job_id},
    ).mappings().fetchone()

    if existing_job:
        existing_fingerprint = existing_job["job_fingerprint"]
        new_fingerprint = str(job["job_fingerprint"])

        if existing_fingerprint and existing_fingerprint != new_fingerprint:
            # Snapshot the PREVIOUS state
            snapshot_data = dict(existing_job)
            snapshot_data["job_id"] = canonical_job_id
            
            _insert_job_snapshot_in_conn(conn, snapshot_data)

            logger.debug(
                "job_snapshot_created",
                extra={
                    "job_id": canonical_job_id,
                    "fingerprint": new_fingerprint
                }
            )

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
                geo_class,
                company_id,
                job_uid,
                job_fingerprint,
                source_schema_hash,
                policy_version,
                compliance_status,
                compliance_score,
                job_family,
                job_role,
                seniority,
                specialization,
                job_quality_score,
                salary_min,
                salary_max,
                salary_currency,
                salary_period,
                salary_source,
                salary_min_eur,
                salary_max_eur,
                salary_transparency_status,
                source_department
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
                :geo_class,
                :company_id,
                :job_uid,
                :job_fingerprint,
                :source_schema_hash,
                :policy_version,
                :compliance_status,
                :compliance_score,
                :job_family,
                :job_role,
                :seniority,
                :specialization,
                :job_quality_score,
                :salary_min,
                :salary_max,
                :salary_currency,
                :salary_period,
                :salary_source,
                :salary_min_eur,
                :salary_max_eur,
                :salary_transparency_status,
                :source_department
            )
            ON CONFLICT (job_id) DO UPDATE SET
                source = COALESCE(jobs.source, excluded.source),
                source_job_id = COALESCE(jobs.source_job_id, excluded.source_job_id),
                source_url = COALESCE(jobs.source_url, excluded.source_url),
                title = excluded.title,
                company_name = excluded.company_name,
                description = excluded.description,
                remote_source_flag = excluded.remote_source_flag,
                remote_scope = excluded.remote_scope,
                status = excluded.status,
                remote_class = excluded.remote_class,
                geo_class = excluded.geo_class,
                company_id = COALESCE(jobs.company_id, excluded.company_id),
                job_uid = excluded.job_uid,
                job_fingerprint = excluded.job_fingerprint,
                source_schema_hash = excluded.source_schema_hash,
                policy_version = excluded.policy_version,
                compliance_status = excluded.compliance_status,
                compliance_score = excluded.compliance_score,
                job_family = excluded.job_family,
                job_role = excluded.job_role,
                seniority = excluded.seniority,
                specialization = excluded.specialization,
                job_quality_score = excluded.job_quality_score,
                salary_min = excluded.salary_min,
                salary_max = excluded.salary_max,
                salary_currency = excluded.salary_currency,
                salary_period = excluded.salary_period,
                salary_source = excluded.salary_source,
                salary_min_eur = excluded.salary_min_eur,
                salary_max_eur = excluded.salary_max_eur,
                salary_transparency_status = excluded.salary_transparency_status,
                source_department = excluded.source_department,
                first_seen_at = CASE
                    WHEN excluded.first_seen_at < jobs.first_seen_at
                    THEN excluded.first_seen_at
                    ELSE jobs.first_seen_at
                END,
                last_seen_at = excluded.last_seen_at
        """),
        {
            "job_id": canonical_job_id,
            "source": resolved_source,
            "source_job_id": resolved_source_job_id,
            "source_url": resolved_source_url,
            "title": job["title"],
            "company_name": job["company_name"],
            "description": job["description"],
            "remote_source_flag": bool(job["remote_source_flag"]),
            "remote_scope": job["remote_scope"],
            "status": job["status"],
            "first_seen_at": first_seen_at,
            "last_seen_at": now,
            "remote_class": job.get("remote_class"),
            "geo_class": job.get("geo_class"),
            "company_id": job.get("company_id") or company_id,
            "job_uid": job.get("job_uid"),
            "job_fingerprint": job.get("job_fingerprint"),
            "source_schema_hash": job.get("source_schema_hash"),
            "policy_version": job.get("policy_version"),
            "compliance_status": job.get("compliance_status"),
            "compliance_score": job.get("compliance_score"),
            "job_family": job.get("job_family"),
            "job_role": job.get("job_role"),
            "seniority": job.get("seniority"),
            "specialization": job.get("specialization"),
            "job_quality_score": job.get("job_quality_score"),
            "salary_min": int(job["salary_min"]) if job.get("salary_min") is not None else None,
            "salary_max": int(job["salary_max"]) if job.get("salary_max") is not None else None,
            "salary_currency": job.get("salary_currency"),
            "salary_period": job.get("salary_period"),
            "salary_source": job.get("salary_source"),
            "salary_min_eur": int(job["salary_min_eur"]) if job.get("salary_min_eur") is not None else None,
            "salary_max_eur": int(job["salary_max_eur"]) if job.get("salary_max_eur") is not None else None,
            "salary_transparency_status": job.get("salary_transparency_status"),
            "source_department": str(job.get("department"))[:255] if job.get("department") else None,
        },
    )

    _upsert_job_source_mapping_in_conn(
        conn,
        job_id=canonical_job_id,
        source=resolved_source,
        source_job_id=resolved_source_job_id,
        source_url=resolved_source_url,
        first_seen_at=first_seen_at,
        now=now,
    )

    return canonical_job_id

def upsert_job(job: dict, conn: Connection | None = None, *, company_id: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    first_seen_at = job.get("first_seen_at") or now

    target_conn = _require_open_conn(conn, op_name="upsert_job")
    return _upsert_job_in_conn(
        target_conn,
        job=job,
        first_seen_at=first_seen_at,
        now=now,
        company_id=company_id,
    )
