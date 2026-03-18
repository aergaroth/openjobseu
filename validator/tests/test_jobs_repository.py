import uuid
from sqlalchemy import text
from storage.db_engine import get_engine
from storage.repositories.jobs_repository import upsert_job


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


def test_upsert_job_creates_snapshot_on_fingerprint_change():
    engine = get_engine()

    # 1. Create an initial job
    job_data = make_job(
        title="Original Title",
        description="Original description text.",
        remote_class="REMOTE_ONLY",
        geo_class="EU_REGION",
        salary_min=10000,
        salary_max=20000,
        salary_currency="EUR",
    )

    with engine.begin() as conn:
        job_id = upsert_job(job_data, conn=conn)

        # 2. Simulate ATS fetching the same job but with an updated description (changes fingerprint)
        updated_job_data = job_data.copy()
        updated_job_data["description"] = "New description that alters the fingerprint."
        # Remove existing fingerprint to force recalculation
        updated_job_data.pop("job_fingerprint", None)

        upsert_job(updated_job_data, conn=conn)

        # 3. Verify snapshot was created properly and includes the newly added compliance classes
        snapshot = conn.execute(
            text("SELECT * FROM job_snapshots WHERE job_id = :job_id ORDER BY captured_at DESC LIMIT 1"),
            {"job_id": job_id}
        ).mappings().one()

        assert snapshot["title"] == "Original Title"
        assert snapshot["salary_min"] == 10000
        assert snapshot["remote_class"] == "REMOTE_ONLY"
        assert snapshot["geo_class"] == "EU_REGION"