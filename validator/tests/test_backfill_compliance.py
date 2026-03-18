import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from app.main import app
from app.utils.backfill_compliance import backfill_missing_compliance_classes
from storage.db_engine import get_engine
from app.domain.compliance.engine import ENGINE_POLICY_VERSION

client = TestClient(app)

def test_backfill_missing_compliance_classes():
    engine = get_engine()
    
    # 1. Insert jobs with missing/outdated compliance
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO jobs (job_id, job_uid, job_fingerprint, title, description, remote_scope, source, compliance_status)
                VALUES 
                ('id1', 'job1', 'fp1', 'Software Engineer', 'Remote job in EU', 'EU_ONLY', 'source1', NULL),
                ('id2', 'job2', 'fp2', 'Product Manager', 'Office job', 'OFFICE', 'source2', NULL)
            """)
        )
        # Outdated policy
        conn.execute(
            text("""
                INSERT INTO jobs (job_id, job_uid, job_fingerprint, title, description, remote_scope, source, compliance_status, compliance_score, policy_version)
                VALUES 
                ('id3', 'job3', 'fp3', 'Designer', 'Remote job', 'REMOTE', 'source3', 'active', 100, 'v0')
            """)
        )

    # 2. Run backfill
    updated_count = backfill_missing_compliance_classes(limit=10)
    assert updated_count == 3

    # 3. Verify results
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT job_uid, compliance_status, policy_version FROM jobs")).mappings().all()
        for row in rows:
            assert row["compliance_status"] is not None
            assert row["policy_version"] == ENGINE_POLICY_VERSION.value

        # Verify reports
        report_count = conn.execute(text("SELECT count(*) FROM compliance_reports")).scalar()
        assert report_count == 3

def test_backfill_endpoint():
    engine = get_engine()
    
    # 1. Insert jobs
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO jobs (job_id, job_uid, job_fingerprint, title, description, remote_scope, source, compliance_status)
                VALUES ('id1', 'job1', 'fp1', 'DevOps', 'Cloud', 'REMOTE', 'source1', NULL)
            """)
        )

    # 2. Call endpoint
    response = client.post("/internal/backfill-compliance?limit=10")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "updated_jobs_count": 1}

    # 3. Verify DB
    with engine.connect() as conn:
        status = conn.execute(text("SELECT compliance_status FROM jobs WHERE job_uid = 'job1'")).scalar()
        assert status is not None
