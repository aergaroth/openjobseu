from datetime import datetime, timezone
from sqlalchemy import text
from storage.db_engine import get_engine
from app.workers.maintenance import run_maintenance_pipeline


def test_maintenance_pipeline_updates_company_stats(db_factory):
    # 1. Tworzymy firmy za pomocą fabryki danych
    comp1 = db_factory.create_company(
        legal_name="Acme EU",
        bootstrap=True,
        is_active=True,
        hq_country="PL",
        remote_posture="REMOTE_ONLY",
        eu_entity_verified=True,
    )
    comp2 = db_factory.create_company(
        legal_name="Acme US",
        bootstrap=True,
        is_active=True,
        hq_country="US",
        remote_posture="UNKNOWN",
        eu_entity_verified=False,
    )
    comp3 = db_factory.create_company(
        legal_name="Acme New",
        bootstrap=True,
        is_active=True,
        hq_country="PL",
        remote_posture="UNKNOWN",
        eu_entity_verified=False,
    )
    comp4 = db_factory.create_company(
        legal_name="Acme Upgrade",
        bootstrap=True,
        is_active=True,
        hq_country="US",
        remote_posture="UNKNOWN",
        eu_entity_verified=False,
    )

    comp1_id = comp1["company_id"]
    comp2_id = comp2["company_id"]
    comp3_id = comp3["company_id"]
    comp4_id = comp4["company_id"]

    now = datetime.now(timezone.utc)

    # 2. Tworzymy oferty przypisane do odpowiednich firm
    db_factory.create_job(
        comp1_id,
        job_id="job-1",
        title="Engineer 1",
        status="active",
        compliance_status="approved",
        salary_transparency_status="disclosed",
        first_seen_at="2023-01-01T10:00:00Z",
        remote_source_flag=True,
    )
    db_factory.create_job(
        comp1_id,
        job_id="job-2",
        title="Engineer 2",
        status="active",
        compliance_status="approved",
        salary_transparency_status="disclosed",
        first_seen_at="2023-01-02T10:00:00Z",
        remote_source_flag=True,
    )
    db_factory.create_job(
        comp1_id,
        job_id="job-3",
        title="Engineer 3",
        status="active",
        compliance_status="rejected",
        salary_transparency_status="disclosed",
        first_seen_at="2023-01-03T10:00:00Z",
        remote_source_flag=False,
    )
    db_factory.create_job(
        comp1_id,
        job_id="job-4",
        title="Engineer 4",
        status="stale",
        compliance_status=None,
        salary_transparency_status="unknown",
        first_seen_at="2023-01-04T10:00:00Z",
        remote_source_flag=False,
    )

    db_factory.create_job(
        comp2_id,
        job_id="job-5",
        title="US Eng",
        status="active",
        compliance_status="approved",
        salary_transparency_status="unknown",
        first_seen_at="2023-01-05T10:00:00Z",
        remote_source_flag=True,
    )

    db_factory.create_job(
        comp3_id,
        job_id="job-6",
        title="New Eng",
        status="active",
        compliance_status="approved",
        salary_transparency_status="unknown",
        first_seen_at=now,
        remote_source_flag=False,
    )

    db_factory.create_job(
        comp4_id,
        job_id="job-7",
        title="Rem 1",
        status="active",
        compliance_status="approved",
        salary_transparency_status="unknown",
        first_seen_at=now,
        remote_source_flag=True,
    )
    db_factory.create_job(
        comp4_id,
        job_id="job-8",
        title="Rem 2",
        status="active",
        compliance_status="approved",
        salary_transparency_status="unknown",
        first_seen_at=now,
        remote_source_flag=True,
    )
    db_factory.create_job(
        comp4_id,
        job_id="job-9",
        title="Rem 3",
        status="active",
        compliance_status="approved",
        salary_transparency_status="unknown",
        first_seen_at=now,
        remote_source_flag=True,
    )

    result = run_maintenance_pipeline()

    assert result["metrics"]["status"] == "ok", f"Pipeline failed: {result['metrics'].get('error')}"
    assert result["metrics"]["job_stats_updated"] >= 3
    assert result["metrics"]["scores_updated"] >= 3
    assert result["metrics"]["posture_updated"] >= 1

    engine = get_engine()
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT company_id, is_active, remote_posture, approved_jobs_count, rejected_jobs_count, total_jobs_count, last_active_job_at, signal_score FROM companies ORDER BY legal_name"
                )
            )
            .mappings()
            .all()
        )

        # comp-1: 2 approved jobs.
        # Score = (PL (+20) + REMOTE_ONLY (+40) + EU entity (+25) + ratio 2/4=0.5 (+8)) = 93
        # Transparency ratio 3/4 = 0.75 >= 0.5 -> Multiplier 1.2 -> 93 * 1.2 = 111.6 -> 112
        assert str(rows[0]["company_id"]) == comp1_id
        assert rows[0]["is_active"] is True
        assert rows[0]["total_jobs_count"] == 4
        assert rows[0]["approved_jobs_count"] == 2
        assert rows[0]["rejected_jobs_count"] == 1
        assert str(rows[0]["last_active_job_at"]).startswith("2023-01-03")
        assert rows[0]["signal_score"] == 112

        assert str(rows[1]["company_id"]) == comp3_id
        assert rows[1]["is_active"] is True

        # comp-4 (Acme Upgrade) has 3 remote jobs -> Should upgrade to REMOTE_FRIENDLY
        # Score = US (+0) + REMOTE_FRIENDLY (+20) + No EU entity (+0) + ratio 3/3=1.0 (+15) = 35
        assert str(rows[2]["company_id"]) == comp4_id
        assert rows[2]["is_active"] is True
        assert rows[2]["remote_posture"] == "REMOTE_FRIENDLY"
        assert rows[2]["signal_score"] == 35

        # comp-2: 1 approved job.
        # Score = US (+0) + UNKNOWN (+0) + No EU entity (+0) + ratio 1/1=1.0 (+15) = 15
        assert str(rows[3]["company_id"]) == comp2_id
        assert rows[3]["is_active"] is True
        assert rows[3]["total_jobs_count"] == 1
        assert rows[3]["approved_jobs_count"] == 1
        assert rows[3]["rejected_jobs_count"] == 0
        assert str(rows[3]["last_active_job_at"]).startswith("2023-01-05")
        assert rows[3]["signal_score"] == 15
