from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Connection
from storage.db_engine import get_engine
from storage.common import _require_open_conn

engine = get_engine()


def get_jobs_for_verification(limit: int = 20) -> list[dict]:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT
                    job_id,
                    source_url,
                    status,
                    last_verified_at,
                    verification_failures
                FROM jobs
                WHERE
                    status IN ('active', 'stale')
                    AND (last_verified_at IS NULL OR last_verified_at < NOW() - INTERVAL '6 hours')
                ORDER BY
                    COALESCE(last_verified_at, '1970-01-01T00:00:00+00:00') ASC
                LIMIT :limit
            """),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
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
                "availability_status": status,
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
                "availability_status": item["availability_status"],
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
                availability_status = :availability_status,
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
