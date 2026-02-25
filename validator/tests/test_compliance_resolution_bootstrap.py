from app.workers.compliance_resolution import run_compliance_resolution_for_existing_db
from storage.sqlite import init_db, upsert_job
from storage.db import get_engine
from sqlalchemy import text

engine = get_engine()


def _make_job(job_id: str, remote_scope: str, *, remote_source_flag: bool = True) -> dict:
    return {
        "job_id": job_id,
        "source": "remoteok",
        "source_job_id": job_id.split(":")[-1],
        "source_url": f"https://example.com/jobs/{job_id}",
        "title": "Backend Engineer",
        "company_name": "Acme",
        "description": "Role description",
        "remote_source_flag": remote_source_flag,
        "remote_scope": remote_scope,
        "status": "new",
        "first_seen_at": "2026-01-05T10:00:00+00:00",
    }


def test_bootstrap_runs_for_existing_db_rows():
    init_db()

    approved = _make_job("seed:approved", "EU-wide")
    review = _make_job("seed:review", "Poland", remote_source_flag=False)
    rejected = _make_job("seed:rejected", "USA only")

    with engine.begin() as conn:
        upsert_job(approved, conn=conn)
        upsert_job(review, conn=conn)
        upsert_job(rejected, conn=conn)

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE jobs
                SET
                    remote_class = NULL,
                    geo_class = NULL,
                    compliance_status = NULL,
                    compliance_score = NULL
                WHERE job_id IN (:id1, :id2, :id3)
            """),
            {
                "id1": approved["job_id"],
                "id2": review["job_id"],
                "id3": rejected["job_id"],
            },
        )

    summary = run_compliance_resolution_for_existing_db(batch_size=2, max_batches=10)

    assert summary["initial_missing"] >= 3
    assert summary["remaining_missing"] == 0
    assert summary["updated"] >= 3

    with engine.begin() as conn:
        approved_row = conn.execute(
            text("SELECT compliance_status, compliance_score FROM jobs WHERE job_id = :job_id"),
            {"job_id": approved["job_id"]},
        ).fetchone()
        review_row = conn.execute(
            text("SELECT compliance_status, compliance_score FROM jobs WHERE job_id = :job_id"),
            {"job_id": review["job_id"]},
        ).fetchone()
        rejected_row = conn.execute(
            text("SELECT compliance_status, compliance_score FROM jobs WHERE job_id = :job_id"),
            {"job_id": rejected["job_id"]},
        ).fetchone()

    assert approved_row is not None
    assert approved_row[0] == "approved"
    assert approved_row[1] >= 80

    assert review_row is not None
    assert review_row[0] == "review"
    assert 50 <= review_row[1] <= 79

    assert rejected_row is not None
    assert rejected_row[0] == "rejected"
    assert rejected_row[1] == 0
