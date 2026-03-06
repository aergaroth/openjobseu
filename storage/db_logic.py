''' 
this file now uses SQLAlchemy Core for database interactions, 
but retains the same function signatures and overall structure 
as before to minimize impact on other parts of the codebase. 
'''

import json
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Connection
from app.domain.classification.enums import GeoClass, RemoteClass
from app.domain.compliance.engine import ENGINE_POLICY_VERSION
from app.domain.compliance.classifiers.geo import classify_geo_scope
from app.domain.jobs.identity import (
    compute_job_fingerprint,
    compute_job_uid,
    compute_schema_hash,
)
from storage.db_engine import get_engine
from app.domain.classification.mappers import normalize_geo_class, normalize_remote_class

engine = get_engine()
MIGRATIONS_PATH = Path("storage/migrations")


def _string_like(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value

    return str(value)


def _derive_remote_class(job: dict) -> str:
    compliance = job.get("_compliance")
    if not isinstance(compliance, dict):
        return (
            RemoteClass.REMOTE_ONLY.value
            if bool(job.get("remote_source_flag"))
            else RemoteClass.UNKNOWN.value
        )

    policy_reason = (_string_like(compliance.get("policy_reason")) or "").strip().lower()
    remote_model = _string_like(compliance.get("remote_model"))

    if policy_reason == RemoteClass.NON_REMOTE.value:
        return RemoteClass.NON_REMOTE.value

    return normalize_remote_class(remote_model).value


def _normalize_geo_class_value(value: object | None) -> str:
    return normalize_geo_class(_string_like(value)).value


def _derive_geo_class(job: dict) -> str:
    
    explicit_geo = job.get("geo_class")
    if explicit_geo:
        normalized_explicit_geo = _normalize_geo_class_value(explicit_geo)
        if normalized_explicit_geo != GeoClass.UNKNOWN.value:
            return normalized_explicit_geo

    compliance = job.get("_compliance")
    policy_reason = ""
    explicit_geo_class = None

    if isinstance(compliance, dict):
        policy_reason = (_string_like(compliance.get("policy_reason")) or "").strip().lower()
        explicit_geo_class = compliance.get("geo_class")

    if explicit_geo_class:
        normalized = _normalize_geo_class_value(explicit_geo_class)
        if normalized != GeoClass.UNKNOWN.value:
            return normalized

    if policy_reason in {"geo_restriction", "geo_restriction_hard"}:
        return GeoClass.NON_EU.value

    classifier_result = classify_geo_scope(
        str(job.get("title") or ""),
        str(job.get("description") or ""),
    )
    normalized_classifier_geo = _normalize_geo_class_value(classifier_result.get("geo_class"))
    if normalized_classifier_geo != GeoClass.UNKNOWN.value:
        return normalized_classifier_geo

    remote_scope = str(job.get("remote_scope") or "").strip()
    if remote_scope:
        remote_scope_result = classify_geo_scope(remote_scope, "")
        normalized_remote_scope_geo = _normalize_geo_class_value(remote_scope_result.get("geo_class"))
        if normalized_remote_scope_geo != GeoClass.UNKNOWN.value:
            return normalized_remote_scope_geo

    return GeoClass.UNKNOWN.value


def _resolve_company_identity(company_id: str | None, job: dict) -> str:
    if company_id:
        return str(company_id)
    embedded_company = job.get("company_id")
    if embedded_company:
        return str(embedded_company)
    return ""


def _derive_job_uid(job: dict, company_id: str | None) -> str:
    explicit_job_uid = _string_like(job.get("job_uid"))
    if explicit_job_uid:
        return explicit_job_uid

    return compute_job_uid(
        company_id=_resolve_company_identity(company_id, job),
        title=str(job.get("title") or ""),
        location=str(job.get("remote_scope") or ""),
        description=str(job.get("description") or ""),
    )


def _derive_job_fingerprint(job: dict, company_id: str | None) -> str:
    explicit_fingerprint = _string_like(job.get("job_fingerprint"))
    if explicit_fingerprint:
        return explicit_fingerprint

    return compute_job_fingerprint(
        str(job.get("description") or ""),
        title=str(job.get("title") or ""),
        location=str(job.get("remote_scope") or ""),
        company_id=_resolve_company_identity(company_id, job),
        company_name=str(job.get("company_name") or ""),
    )


def _derive_source_schema_hash(job: dict) -> str | None:
    explicit_schema_hash = _string_like(job.get("source_schema_hash"))
    if explicit_schema_hash:
        return explicit_schema_hash

    if "source_payload" not in job:
        return None
    source_payload = job.get("source_payload")
    if source_payload is None:
        return None
    return compute_schema_hash(source_payload)


def _derive_policy_version(job: dict) -> str:
    explicit_policy_version = (_string_like(job.get("policy_version")) or "").strip()
    if explicit_policy_version:
        return explicit_policy_version

    compliance = job.get("_compliance")
    if isinstance(compliance, dict):
        compliance_policy_version = (_string_like(compliance.get("policy_version")) or "").strip()
        if compliance_policy_version:
            if compliance_policy_version.lower().startswith("v"):
                return compliance_policy_version
            try:
                numeric = float(compliance_policy_version)
                if numeric.is_integer():
                    return f"v{int(numeric)}"
            except ValueError:
                pass
            return compliance_policy_version

    return ENGINE_POLICY_VERSION.value


def _derive_source_fields(job: dict) -> tuple[str, str, str | None]:
    source = (_string_like(job.get("source")) or "").strip()
    source_job_id = (_string_like(job.get("source_job_id")) or "").strip()
    source_url = _string_like(job.get("source_url"))

    if not source:
        raise ValueError("job.source is required")
    if not source_job_id:
        raise ValueError("job.source_job_id is required")

    return source, source_job_id, source_url


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
                source_url = COALESCE(excluded.source_url, job_sources.source_url),
                first_seen_at = CASE
                    WHEN excluded.first_seen_at < job_sources.first_seen_at
                    THEN excluded.first_seen_at
                    ELSE job_sources.first_seen_at
                END,
                last_seen_at = excluded.last_seen_at,
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


def init_db():
    db_engine = get_engine()

    with db_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL
            )
        """))

        applied_rows = conn.execute(text("SELECT version FROM schema_migrations"))
        applied_versions = {row[0] for row in applied_rows}

        migration_files = sorted(MIGRATIONS_PATH.glob("*.sql"))
        migration_versions = {int(file.name.split("_")[0]) for file in migration_files}

        if not applied_versions:
            existing_jobs = conn.execute(
                text("SELECT to_regclass('public.jobs')")
            ).scalar_one_or_none()
            existing_companies = conn.execute(
                text("SELECT to_regclass('public.companies')")
            ).scalar_one_or_none()

            if existing_jobs and existing_companies:
                # Legacy databases may already contain baseline tables but miss
                # the migration ledger. Mark only baseline schema as applied so
                # newer migrations still run.
                baseline_versions = {1, 2} & migration_versions
                now = datetime.now(timezone.utc)
                conn.execute(
                    text("""
                        INSERT INTO schema_migrations (version, applied_at)
                        VALUES (:version, :applied_at)
                        ON CONFLICT (version) DO NOTHING
                    """),
                    [
                        {"version": version, "applied_at": now}
                        for version in sorted(baseline_versions)
                    ],
                )
                applied_versions = set(baseline_versions)

        for migration_file in migration_files:
            version = int(migration_file.name.split("_")[0])
            if version in applied_versions:
                continue

            sql = migration_file.read_text()
            conn.execute(text(sql))
            conn.execute(
                text("""
                    INSERT INTO schema_migrations (version, applied_at)
                    VALUES (:version, :applied_at)
                """),
                {"version": version, "applied_at": datetime.now(timezone.utc)},
            )


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
    company_id: str | None = None,
) -> str:
    resolved_company_id = _resolve_company_identity(company_id, job) or None
    resolved_source, resolved_source_job_id, resolved_source_url = _derive_source_fields(job)
    resolved_job_uid = _derive_job_uid(job, resolved_company_id)
    resolved_job_fingerprint = _derive_job_fingerprint(job, resolved_company_id)
    resolved_source_schema_hash = _derive_source_schema_hash(job)
    resolved_policy_version = _derive_policy_version(job)
    canonical_job_id = _resolve_canonical_job_id(
        conn,
        incoming_job_id=str(job["job_id"]),
        source=resolved_source,
        source_job_id=resolved_source_job_id,
        job_fingerprint=resolved_job_fingerprint,
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
                compliance_score
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
                :compliance_score
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
            "remote_class": remote_class,
            "geo_class": geo_class,
            "company_id": resolved_company_id,
            "job_uid": resolved_job_uid,
            "job_fingerprint": resolved_job_fingerprint,
            "source_schema_hash": resolved_source_schema_hash,
            "policy_version": resolved_policy_version,
            "compliance_status": job.get("compliance_status"),
            "compliance_score": job.get("compliance_score"),
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
    remote_class = _derive_remote_class(job)
    geo_class = _derive_geo_class(job)

    target_conn = _require_open_conn(conn, op_name="upsert_job")
    return _upsert_job_in_conn(
        target_conn,
        job=job,
        first_seen_at=first_seen_at,
        now=now,
        remote_class=remote_class,
        geo_class=geo_class,
        company_id=company_id,
    )


def insert_compliance_report(
    conn: Connection,
    *,
    job_id: str,
    job_uid: str,
    policy_version: str,
    remote_class: str | None,
    geo_class: str | None,
    hard_geo_flag: bool,
    base_score: int,
    penalties: dict | None = None,
    bonuses: dict | None = None,
    final_score: int,
    final_status: str,
    decision_vector: dict | None = None,
) -> None:
    """Insert a compliance report for a job."""
    conn.execute(
        text("""
            INSERT INTO compliance_reports (
                job_id, job_uid, policy_version, remote_class, geo_class,
                hard_geo_flag, base_score, penalties, bonuses,
                final_score, final_status, decision_vector, created_at
            )
            VALUES (
                :job_id, :job_uid, :policy_version, :remote_class, :geo_class,
                :hard_geo_flag, :base_score, :penalties, :bonuses,
                :final_score, :final_status, :decision_vector, NOW()
            )
            ON CONFLICT (job_uid, policy_version) DO UPDATE SET
                job_id = EXCLUDED.job_id,
                remote_class = EXCLUDED.remote_class,
                geo_class = EXCLUDED.geo_class,
                hard_geo_flag = EXCLUDED.hard_geo_flag,
                base_score = EXCLUDED.base_score,
                penalties = EXCLUDED.penalties,
                bonuses = EXCLUDED.bonuses,
                final_score = EXCLUDED.final_score,
                final_status = EXCLUDED.final_status,
                decision_vector = EXCLUDED.decision_vector,
                created_at = NOW()
        """),
        {
            "job_id": job_id,
            "job_uid": job_uid,
            "policy_version": policy_version,
            "remote_class": remote_class,
            "geo_class": geo_class,
            "hard_geo_flag": hard_geo_flag,
            "base_score": base_score,
            "penalties": json.dumps(penalties, default=str) if penalties is not None else None,
            "bonuses": json.dumps(bonuses, default=str) if bonuses is not None else None,
            "final_score": final_score,
            "final_status": final_status,
            "decision_vector": json.dumps(decision_vector, default=str)
            if decision_vector is not None
            else None,
        },
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
                "remote_model": RemoteClass.UNKNOWN.value,
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
        clauses.append(
            "EXISTS ("
            "SELECT 1 FROM job_sources js_filter "
            f"WHERE js_filter.job_id = jobs.job_id AND js_filter.source = :p{param_counter}"
            ")"
        )
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


def get_compliance_stats_last_7d() -> dict:
    with engine.connect() as conn:
        row = conn.execute(
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
        ).mappings().one()

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
        rows = conn.execute(
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
        ).mappings().all()

    return [str(row["source"]) for row in rows]


def get_audit_company_compliance_stats(
    *,
    min_total_jobs: int = 10,
) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
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
                ORDER BY approved_ratio_pct ASC NULLS FIRST, c.legal_name ASC
            """),
            {"min_total_jobs": int(min_total_jobs)},
        ).mappings().all()

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
        rows = conn.execute(
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
                ORDER BY approved_ratio_pct ASC NULLS FIRST, js.source ASC
            """)
        ).mappings().all()

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

    with engine.connect() as conn:
        rows = conn.execute(
            text(query),
            params,
        ).mappings().all()

    return [dict(row) for row in rows]
