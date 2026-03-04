import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from storage.db_engine import get_engine
from storage.db_logic import init_db, upsert_job

client = TestClient(app)
engine = get_engine()


def _make_job(job_id: str) -> dict:
    return {
        "job_id": job_id,
        "source": "remotive",
        "source_job_id": job_id.split(":")[-1],
        "source_url": f"https://example.com/jobs/{job_id}",
        "title": f"{job_id} title",
        "company_name": "Example Co",
        "description": "Example description",
        "remote_source_flag": True,
        "remote_scope": "Europe",
        "status": "new",
        "first_seen_at": "2026-01-01T10:00:00+00:00",
    }


def test_jobs_compliance_stats_7d_empty():
    response = client.get("/jobs/stats/compliance-7d")
    assert response.status_code == 200
    payload = response.json()

    assert payload["window"] == "last_7_days"
    assert payload["total_jobs"] == 0
    assert payload["approved"] == 0
    assert payload["review"] == 0
    assert payload["rejected"] == 0
    assert payload["approved_ratio_pct"] is None


def test_jobs_compliance_stats_7d_aggregates_recent_rows():
    init_db()

    with engine.begin() as conn:
        upsert_job(_make_job("stats:approved_recent"), conn=conn)
        upsert_job(_make_job("stats:review_recent"), conn=conn)
        upsert_job(_make_job("stats:rejected_recent"), conn=conn)
        upsert_job(_make_job("stats:approved_old"), conn=conn)

        conn.execute(
            text("""
                UPDATE jobs
                SET
                    compliance_status = CASE
                        WHEN job_id = 'stats:approved_recent' THEN 'approved'
                        WHEN job_id = 'stats:review_recent' THEN 'review'
                        WHEN job_id = 'stats:rejected_recent' THEN 'rejected'
                        WHEN job_id = 'stats:approved_old' THEN 'approved'
                    END,
                    compliance_score = CASE
                        WHEN job_id = 'stats:approved_recent' THEN 100
                        WHEN job_id = 'stats:review_recent' THEN 60
                        WHEN job_id = 'stats:rejected_recent' THEN 0
                        WHEN job_id = 'stats:approved_old' THEN 100
                    END,
                    first_seen_at = CASE
                        WHEN job_id = 'stats:approved_old' THEN NOW() - INTERVAL '8 days'
                        ELSE NOW() - INTERVAL '2 days'
                    END
                WHERE job_id IN (
                    'stats:approved_recent',
                    'stats:review_recent',
                    'stats:rejected_recent',
                    'stats:approved_old'
                )
            """)
        )

    response = client.get("/jobs/stats/compliance-7d")
    assert response.status_code == 200
    payload = response.json()

    assert payload["window"] == "last_7_days"
    assert payload["total_jobs"] == 3
    assert payload["approved"] == 1
    assert payload["review"] == 1
    assert payload["rejected"] == 1
    assert payload["approved_ratio_pct"] == pytest.approx(33.33, abs=0.01)
