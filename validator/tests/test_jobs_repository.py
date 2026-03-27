import uuid
from sqlalchemy import text
from storage.repositories.jobs_repository import get_jobs, get_jobs_paginated, upsert_job


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


def test_upsert_job_generates_identity_salary_and_source_mapping_when_missing(db_factory):
    company = db_factory.create_company(legal_name="Identity Co")
    job_to_insert = {
        "job_id": str(uuid.uuid4()),
        "source": "greenhouse:identity",
        "source_job_id": "src-identity-1",
        "source_url": "https://example.com/jobs/identity",
        "company_id": company["company_id"],
        "company_name": company["legal_name"],
        "title": "Data Engineer",
        "description": "Our compensation package includes a base salary of $100k - $120k per year.",
        "status": "new",
        "remote_source_flag": True,
        "remote_scope": "Europe",
    }

    with db_factory.engine.begin() as conn:
        job_id = upsert_job(job_to_insert, conn=conn)
        job_row = (
            conn.execute(
                text("""
                    SELECT job_uid, job_fingerprint, salary_min, salary_max, salary_currency
                    , salary_min_eur, salary_max_eur
                    FROM jobs
                    WHERE job_id = :job_id
                """),
                {"job_id": job_id},
            )
            .mappings()
            .one()
        )
        source_row = (
            conn.execute(
                text("""
                SELECT source, source_job_id, job_id, seen_count
                FROM job_sources
                WHERE source = :source AND source_job_id = :source_job_id
            """),
                {"source": "greenhouse:identity", "source_job_id": "src-identity-1"},
            )
            .mappings()
            .one()
        )

    assert job_row["job_uid"]
    assert job_row["job_fingerprint"]
    assert job_row["salary_min"] == 100000
    assert job_row["salary_max"] == 120000
    assert job_row["salary_currency"] == "USD"
    assert job_row["salary_min_eur"] == 92000
    assert job_row["salary_max_eur"] == 110400
    assert source_row["job_id"] == job_id
    assert int(source_row["seen_count"]) == 1


def test_upsert_job_preserves_first_seen_at_and_avoids_snapshot_without_material_change(db_factory):
    company = db_factory.create_company()
    original_job = {
        "job_id": "job-preserve-first-seen",
        "source": "lever:acme",
        "source_job_id": "42",
        "source_url": "https://example.com/jobs/42",
        "company_id": company["company_id"],
        "company_name": company["legal_name"],
        "title": "Platform Engineer",
        "description": "Build internal platforms.",
        "status": "new",
        "remote_source_flag": True,
        "remote_scope": "Europe",
        "first_seen_at": "2026-01-01T08:00:00+00:00",
    }
    repeated_job = dict(original_job)
    repeated_job["job_id"] = "job-duplicate-id"
    repeated_job["first_seen_at"] = "2026-01-20T08:00:00+00:00"

    with db_factory.engine.begin() as conn:
        first_job_id = upsert_job(original_job, conn=conn)
        second_job_id = upsert_job(repeated_job, conn=conn)

        row = (
            conn.execute(
                text("""
                SELECT first_seen_at, last_seen_at
                FROM jobs
                WHERE job_id = :job_id
            """),
                {"job_id": first_job_id},
            )
            .mappings()
            .one()
        )
        source_row = (
            conn.execute(
                text("""
                SELECT seen_count, first_seen_at
                FROM job_sources
                WHERE source = 'lever:acme' AND source_job_id = '42'
            """)
            )
            .mappings()
            .one()
        )
        snapshot_count = conn.execute(text("SELECT COUNT(*) FROM job_snapshots")).scalar_one()

    assert first_job_id == second_job_id
    assert str(row["first_seen_at"]).startswith("2026-01-01")
    assert row["last_seen_at"] is not None
    assert int(source_row["seen_count"]) == 2
    assert str(source_row["first_seen_at"]).startswith("2026-01-01")
    assert int(snapshot_count) == 0


def test_get_jobs_and_paginated_support_core_filters(db_factory):
    company_a = db_factory.create_company(legal_name="Acme Labs")
    company_b = db_factory.create_company(legal_name="Beta Systems")
    db_factory.create_job(
        company_a["company_id"],
        job_id="job-acme-1",
        title="Backend Engineer",
        company_name=company_a["legal_name"],
        status="active",
        remote_scope="Europe",
        compliance_score=85,
        first_seen_at="2026-01-03T10:00:00+00:00",
    )
    db_factory.create_job_source("job-acme-1", source="greenhouse:acme", source_job_id="a1")
    db_factory.create_job(
        company_a["company_id"],
        job_id="job-acme-2",
        title="Product Designer",
        company_name=company_a["legal_name"],
        status="expired",
        remote_scope="Worldwide",
        compliance_score=40,
        first_seen_at="2026-01-02T10:00:00+00:00",
    )
    db_factory.create_job_source("job-acme-2", source="lever:acme", source_job_id="a2")
    db_factory.create_job(
        company_b["company_id"],
        job_id="job-beta-1",
        title="Data Engineer",
        company_name=company_b["legal_name"],
        status="new",
        remote_scope="Europe",
        compliance_score=90,
        first_seen_at="2026-01-01T10:00:00+00:00",
    )
    db_factory.create_job_source("job-beta-1", source="greenhouse:beta", source_job_id="b1")

    visible_jobs = get_jobs(status="visible", remote_scope="Europe", min_compliance_score=80)
    search_jobs, total = get_jobs_paginated(q="Acme", source="greenhouse:acme", limit=10, offset=0)

    assert [job["job_id"] for job in visible_jobs] == ["job-acme-1", "job-beta-1"]
    assert total == 1
    assert [job["job_id"] for job in search_jobs] == ["job-acme-1"]
