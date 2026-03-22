import uuid
from sqlalchemy import text
from storage.repositories.jobs_repository import upsert_job


def test_upsert_job_extracts_and_normalizes_salary_to_eur(db_factory):
    # 1. Setup
    company = db_factory.create_company()

    # 2. Test Data
    job_to_insert = {
        "job_id": str(uuid.uuid4()),
        "source": "test_source",
        "source_job_id": "src_123",
        "source_url": "https://example.com/jobs/123",
        "company_id": company["company_id"],
        "company_name": company["legal_name"],
        "title": "Test Job",
        "description": "Our compensation package includes a base salary of $100k - $120k per year.",
        "status": "new",
        "remote_source_flag": False,
        "remote_scope": "Europe",
    }
    expected_min_eur = 92000  # 100000 * 0.92
    expected_max_eur = 110400  # 120000 * 0.92

    # 3. Action & Verification
    with db_factory.engine.begin() as conn:
        job_id = upsert_job(job_to_insert, conn=conn)
        result = (
            conn.execute(
                text("SELECT salary_min_eur, salary_max_eur FROM jobs WHERE job_id = :job_id"),
                {"job_id": job_id},
            )
            .mappings()
            .one()
        )

        assert result["salary_min_eur"] == expected_min_eur
        assert result["salary_max_eur"] == expected_max_eur


def test_upsert_job_creates_snapshot_on_fingerprint_change(db_factory):
    # 1. Setup - tworzymy firmę
    company = db_factory.create_company()

    # Definiujemy początkowy kształt oferty
    job = {
        "job_id": "snap-test-job",
        "job_uid": "snap-uid",
        "job_fingerprint": "old-fingerprint",
        "source": "test_source",
        "source_job_id": "src-123",
        "source_url": "https://example.com/jobs/123",
        "company_id": company["company_id"],
        "company_name": company["legal_name"],
        "title": "Original Title",
        "description": "Original description text.",
        "remote_class": "REMOTE_ONLY",
        "geo_class": "EU_REGION",
        "salary_min": 10000,
        "salary_max": 20000,
        "salary_currency": "EUR",
        "remote_source_flag": True,
        "remote_scope": "Europe",
        "status": "new",
        "first_seen_at": "2026-03-21T12:00:00Z",
    }

    with db_factory.engine.begin() as conn:
        # Wstawienie początkowe (INSERT nie generuje wpisu w logu snapshotów)
        upsert_job(job, conn=conn)

        # 2. Symulujemy, że ATS pobrał zmodyfikowaną ofertę (zmiana fingerprintu aktywuje trigger bazy)
        updated_job_data = dict(job)
        updated_job_data["description"] = "New description that alters the fingerprint."
        updated_job_data["job_fingerprint"] = "new-fingerprint"
        updated_job_data["status"] = "active"

        upsert_job(updated_job_data, conn=conn)

        # 3. Weryfikujemy czy trigger bazy danych poprawnie zarchiwizował STARY stan oferty
        snapshots = (
            conn.execute(
                text("SELECT * FROM job_snapshots WHERE job_id = :job_id ORDER BY captured_at DESC"),
                {"job_id": job["job_id"]},
            )
            .mappings()
            .all()
        )

        assert len(snapshots) == 1

        archived_snapshot = snapshots[0]
        assert archived_snapshot["job_fingerprint"] == "old-fingerprint"
        assert archived_snapshot["title"] == "Original Title"
        assert archived_snapshot["salary_min"] == 10000
        assert archived_snapshot["remote_class"] == "REMOTE_ONLY"
        assert archived_snapshot["geo_class"] == "EU_REGION"
