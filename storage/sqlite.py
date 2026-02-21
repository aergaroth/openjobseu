import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from app.workers.policy.v2.geo_classifier import classify_geo_scope


def get_db_path() -> Path:
    path = Path(os.getenv("OPENJOBSEU_DB_PATH", "data/openjobseu.db"))
    path.parent.mkdir(exist_ok=True)
    return path


def get_conn():
    return sqlite3.connect(get_db_path())


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
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
          job_id TEXT PRIMARY KEY,
          source TEXT,
          source_job_id TEXT,
          source_url TEXT,
	      title TEXT,
	      company_name TEXT,
	      description TEXT,
	      remote_source_flag INTEGER,
	      remote_scope TEXT,
	      status TEXT,
	      first_seen_at TEXT,
	      last_seen_at TEXT,
	      last_verified_at TEXT,
	      verification_failures INTEGER DEFAULT 0,
	      updated_at TEXT,
          remote_class TEXT DEFAULT NULL,
          geo_class TEXT DEFAULT NULL,
          
          policy_v1_decision TEXT DEFAULT NULL,
          policy_v1_reason TEXT DEFAULT NULL,

          policy_v2_decision TEXT DEFAULT NULL,
          policy_v2_reason TEXT DEFAULT NULL,

          compliance_status TEXT DEFAULT NULL,
          compliance_score INTEGER DEFAULT NULL
         
        )
        """)

def upsert_job(job: dict):
    """
    Idempotent upsert of a job record.

    Ingestion is treated as the source of truth for all job metadata
    (title, company, description, remote_scope, etc.).
    On conflict, all ingestion fields are refreshed to allow
    canonical model evolution over time.

    Availability and lifecycle workers may later update status-related fields.
    """
    now = datetime.now(timezone.utc).isoformat()
    first_seen_at = job.get("first_seen_at") or now
    remote_class = _derive_remote_class(job)
    geo_class = _derive_geo_class(job)

    with get_conn() as conn:
        conn.execute(
            """
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
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
                    WHEN excluded.first_seen_at < jobs.first_seen_at THEN excluded.first_seen_at
                    ELSE jobs.first_seen_at
                END,
                last_seen_at = excluded.last_seen_at
            """,
            (
                job["job_id"],
                job["source"],
                job["source_job_id"],
                job["source_url"],
                job["title"],
                job["company_name"],
                job["description"],
                int(job["remote_source_flag"]),
                job["remote_scope"],
                job["status"],
                first_seen_at,
                now,
                remote_class,
                geo_class,
            ),
        )


def get_jobs_for_verification(limit: int = 20) -> list[dict]:
    conn = get_conn()
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            job_id,
            source_url,
            status,
            last_verified_at,
            verification_failures
        FROM jobs
        WHERE status IN ('active', 'stale', 'unreachable')
        ORDER BY
            COALESCE(last_verified_at, '1970-01-01') ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()
    return [dict(row) for row in rows]


def update_job_availability(
    job_id: str,
    status: str,
    verified_at: str | None = None,
    failure: bool = False,
):
    if verified_at is None:
        verified_at = datetime.now(timezone.utc).isoformat()

    conn = get_conn()

    conn.execute(
        """
        UPDATE jobs
        SET
            status = ?,
            last_verified_at = ?,
            verification_failures = CASE
                WHEN ? THEN verification_failures + 1
                ELSE 0
            END,
            updated_at = ?
        WHERE job_id = ?
        """,
        (
            status,
            verified_at,
            failure,
            verified_at,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def count_jobs_missing_compliance() -> int:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM jobs
        WHERE compliance_status IS NULL OR compliance_score IS NULL
        """
    ).fetchone()
    conn.close()
    return int(row[0]) if row else 0


def backfill_missing_compliance_classes(limit: int = 1000) -> int:
    conn = get_conn()
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
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
        ORDER BY COALESCE(last_seen_at, '1970-01-01') DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    if not rows:
        conn.close()
        return 0

    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        payload = dict(row)
        if payload.get("policy_v1_reason"):
            payload["_compliance"] = {
                "policy_reason": payload["policy_v1_reason"],
                "remote_model": "unknown",
            }

        remote_class = payload.get("remote_class") or _derive_remote_class(payload)
        geo_class = payload.get("geo_class") or _derive_geo_class(payload)

        conn.execute(
            """
            UPDATE jobs
            SET
                remote_class = ?,
                geo_class = ?,
                updated_at = ?
            WHERE job_id = ?
            """,
            (
                remote_class,
                geo_class,
                now,
                payload["job_id"],
            ),
        )

    conn.commit()
    conn.close()
    return len(rows)


def get_jobs_for_compliance_resolution(
    limit: int = 500,
    only_missing: bool = False,
) -> list[dict]:
    conn = get_conn()
    conn.row_factory = sqlite3.Row

    where_clause = ""
    if only_missing:
        where_clause = "WHERE compliance_status IS NULL OR compliance_score IS NULL"

    rows = conn.execute(
        f"""
        SELECT
            job_id,
            remote_class,
            geo_class
        FROM jobs
        {where_clause}
        ORDER BY COALESCE(last_seen_at, '1970-01-01') DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()
    return [dict(row) for row in rows]


def update_job_compliance_resolution(
    job_id: str,
    compliance_status: str,
    compliance_score: int,
):
    now = datetime.now(timezone.utc).isoformat()

    conn = get_conn()
    conn.execute(
        """
        UPDATE jobs
        SET
            compliance_status = ?,
            compliance_score = ?,
            updated_at = ?
        WHERE job_id = ?
        """,
        (
            compliance_status,
            compliance_score,
            now,
            job_id,
        ),
    )
    conn.commit()
    conn.close()


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
    conn = get_conn()
    conn.row_factory = sqlite3.Row

    query = """
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
    """

    clauses = []
    params = []

    if status == "visible":
        clauses.append("status IN ('new', 'active')")
    elif status:
        clauses.append("status = ?")
        params.append(status)

    if company:
        clauses.append("LOWER(company_name) LIKE ?")
        params.append(f"%{company.lower()}%")

    if title:
        clauses.append("LOWER(title) LIKE ?")
        params.append(f"%{title.lower()}%")

    if source:
        clauses.append("source = ?")
        params.append(source)

    if remote_scope:
        clauses.append("remote_scope = ?")
        params.append(remote_scope)

    if min_compliance_score is not None:
        clauses.append("COALESCE(compliance_score, 0) >= ?")
        params.append(int(min_compliance_score))

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY first_seen_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]
