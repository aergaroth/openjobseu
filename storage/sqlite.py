import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("data/openjobseu.db")
DB_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    return sqlite3.connect(DB_PATH)

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
    now = datetime.now(timezone.utc).isoformat()

    with get_conn() as conn:
        conn.execute("""
        INSERT INTO jobs (
          job_id, source, source_job_id, source_url,
          title, company_name, description,
          remote, remote_scope, status,
          first_seen_at, last_seen_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
          last_seen_at = excluded.last_seen_at
        """, (
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
            now,
            now,
        ))


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
