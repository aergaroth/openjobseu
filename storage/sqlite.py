import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

def get_db_path() -> Path:
    path = Path(os.getenv("OPENJOBSEU_DB_PATH", "data/openjobseu.db"))
    path.parent.mkdir(exist_ok=True)
    return path

def get_conn():
    return sqlite3.connect(get_db_path())


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
	      remote INTEGER,
	      remote_scope TEXT,
	      status TEXT,
	      first_seen_at TEXT,
	      last_seen_at TEXT,
	      last_verified_at TEXT,
	      verification_failures INTEGER DEFAULT 0,
	      updated_at TEXT
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
                remote,
                remote_scope,
                status,
                first_seen_at,
                last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                source_url = excluded.source_url,
                title = excluded.title,
                company_name = excluded.company_name,
                description = excluded.description,
                remote = excluded.remote,
                remote_scope = excluded.remote_scope,
                status = excluded.status,
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
                int(job["remote"]),
                job["remote_scope"],
                job["status"],
                first_seen_at,
                now,
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


def get_jobs(
    status: str | None = None,
    company: str | None = None,
    title: str | None = None,
    source: str | None = None,
    remote_scope: str | None = None,
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

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY first_seen_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]
