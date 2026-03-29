import json
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Connection
from storage.db_engine import get_engine
from storage.common import _require_open_conn

engine = get_engine()


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
            "decision_vector": json.dumps(decision_vector, default=str) if decision_vector is not None else None,
        },
    )


def insert_compliance_reports(conn: Connection, reports: list[dict]) -> None:
    """Insert multiple compliance reports in a single bulk operation."""
    if not reports:
        return

    for r in reports:
        if r.get("penalties") is not None:
            r["penalties"] = json.dumps(r["penalties"], default=str)
        if r.get("bonuses") is not None:
            r["bonuses"] = json.dumps(r["bonuses"], default=str)
        if r.get("decision_vector") is not None:
            r["decision_vector"] = json.dumps(r["decision_vector"], default=str)

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
        reports,
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
        rows = (
            conn.execute(
                text(query),
                {"limit": limit},
            )
            .mappings()
            .all()
        )

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


def get_jobs_for_compliance_backfill(conn: Connection, *, limit: int, current_policy_version: str) -> list[dict]:
    """
    Fetches jobs that are missing compliance data or have an outdated policy version.
    """
    query = text("""
        SELECT
            job_id, job_uid, title, description, remote_scope, source,
            company_id, company_name, remote_source_flag,
            remote_class, geo_class, compliance_status, compliance_score, policy_version
        FROM jobs
        WHERE compliance_status IS NULL
           OR compliance_score IS NULL
           OR policy_version IS NULL
           OR policy_version != :current_policy_version
        ORDER BY COALESCE(last_seen_at, '1970-01-01T00:00:00+00:00') DESC
        LIMIT :limit
    """)
    rows = (
        conn.execute(
            query,
            {"limit": limit, "current_policy_version": current_policy_version},
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def update_job_compliance_data(conn: Connection, job_updates: list[dict]) -> None:
    """
    Bulk updates jobs with new compliance data from the backfill process.
    """
    if not job_updates:
        return

    conn.execute(
        text("""
            UPDATE jobs
            SET
                remote_class = :remote_class,
                geo_class = :geo_class,
                compliance_status = :compliance_status,
                compliance_score = :compliance_score,
                policy_version = :policy_version,
                updated_at = :updated_at
            WHERE job_id = :job_id
        """),
        job_updates,
    )
