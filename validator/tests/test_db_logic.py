import uuid
from sqlalchemy import text
from storage.db_engine import get_engine
from storage.db_logic import init_db, upsert_job


def make_job(**overrides):
    """Helper to create a minimal job dict for testing."""
    job_id = str(uuid.uuid4())
    base = {
        "job_id": job_id,
        "source": "test_source",
        "source_job_id": f"src_{job_id}",
        "title": "Test Job",
        "company_name": "Test Company",
        "description": "No salary here.",
        "status": "new",
        "remote_source_flag": False,
        "remote_scope": None,
    }
    base.update(overrides)
    return base


def test_upsert_job_extracts_and_normalizes_salary_to_eur():
    # 1. Setup
    engine = get_engine()
    init_db()  # Ensure schema is up to date

    # 2. Test Data
    job_to_insert = make_job(
        description="Our compensation package includes a base salary of $100k - $120k per year."
    )
    expected_min_eur = 92000  # 100000 * 0.92
    expected_max_eur = 110400  # 120000 * 0.92

    # 3. Action & Verification
    with engine.begin() as conn:
        job_id = upsert_job(job_to_insert, conn=conn)
        result = conn.execute(
            text("SELECT salary_min_eur, salary_max_eur FROM jobs WHERE job_id = :job_id"),
            {"job_id": job_id},
        ).mappings().one()

        assert result["salary_min_eur"] == expected_min_eur
        assert result["salary_max_eur"] == expected_max_eur