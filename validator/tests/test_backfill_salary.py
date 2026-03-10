import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from app.main import app
from app.utils.backfill_salary import backfill_missing_salary_fields
from storage.db_engine import get_engine

client = TestClient(app)

@pytest.fixture
def clean_db():
    engine = get_engine()
    # Mark app as ready for middleware
    app.state.ready = True
    app.state.bootstrap_enforced = False
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM jobs"))
    yield
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM jobs"))

def test_backfill_missing_salary_fields(clean_db):
    engine = get_engine()
    
    # 1. Insert jobs with and without salary
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO jobs (job_id, job_uid, job_fingerprint, title, description, remote_scope, source, salary_min, salary_max)
                VALUES 
                ('id1', 'uid1', 'fp1', 'Software Engineer', 'We pay 100k - 120k USD per year', 'EU_ONLY', 'source1', NULL, NULL),
                ('id2', 'uid2', 'fp2', 'Product Manager', 'Office job, no salary mention', 'OFFICE', 'source2', NULL, NULL),
                ('id3', 'uid3', 'fp3', 'Designer', 'Already has salary', 'REMOTE', 'source3', 50000, 60000)
            """)
        )

    # 2. Run backfill
    updated_count = backfill_missing_salary_fields(limit=10)
    
    # Only id1 should be updated (id2 has no salary in description, id3 already has salary)
    assert updated_count == 1

    # 3. Verify results
    with engine.connect() as conn:
        # id1 should now have salary
        row1 = conn.execute(text("SELECT salary_min, salary_max, salary_currency FROM jobs WHERE job_id = 'id1'")).mappings().one()
        assert row1["salary_min"] == 100000
        assert row1["salary_max"] == 120000
        assert row1["salary_currency"] == "USD"

        # id2 should still be NULL (nothing found)
        row2 = conn.execute(text("SELECT salary_min, salary_max FROM jobs WHERE job_id = 'id2'")).mappings().one()
        assert row2["salary_min"] is None
        assert row2["salary_max"] is None

        # id3 should remain unchanged
        row3 = conn.execute(text("SELECT salary_min, salary_max FROM jobs WHERE job_id = 'id3'")).mappings().one()
        assert row3["salary_min"] == 50000
        assert row3["salary_max"] == 60000

def test_backfill_salary_endpoint(clean_db):
    engine = get_engine()
    
    # 1. Insert job
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO jobs (job_id, job_uid, job_fingerprint, title, description, remote_scope, source, salary_min, salary_max)
                VALUES ('id1', 'uid1', 'fp1', 'DevOps', 'Salary: 80000 EUR yearly', 'REMOTE', 'source1', NULL, NULL)
            """)
        )

    # 2. Call endpoint
    response = client.post("/internal/backfill-salary?limit=10")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "updated_jobs_count": 1}

    # 3. Verify DB
    with engine.connect() as conn:
        row = conn.execute(text("SELECT salary_min, salary_currency FROM jobs WHERE job_id = 'id1'")).mappings().one()
        assert row["salary_min"] == 80000
        assert row["salary_currency"] == "EUR"
