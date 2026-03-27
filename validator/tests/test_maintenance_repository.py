from sqlalchemy import text

from storage.repositories.maintenance_repository import (
    update_company_job_stats_bulk,
    update_company_remote_posture_bulk,
    update_company_signal_scores_bulk,
)


def test_maintenance_repository_updates_stats_posture_scores_and_is_idempotent(db_factory):
    company_remote = db_factory.create_company(
        legal_name="Remote Co",
        hq_country="PL",
        remote_posture="UNKNOWN",
        eu_entity_verified=True,
    )
    company_static = db_factory.create_company(
        legal_name="Static Co",
        hq_country="US",
        remote_posture="UNKNOWN",
        eu_entity_verified=False,
    )

    for idx in range(3):
        db_factory.create_job(
            company_remote["company_id"],
            job_id=f"remote-job-{idx}",
            title=f"Remote Job {idx}",
            company_name=company_remote["legal_name"],
            status="active",
            compliance_status="approved",
            salary_transparency_status="disclosed",
            remote_source_flag=True,
            first_seen_at=f"2026-01-0{idx + 1}T10:00:00+00:00",
        )

    db_factory.create_job(
        company_remote["company_id"],
        job_id="remote-job-rejected",
        title="Rejected Job",
        company_name=company_remote["legal_name"],
        status="expired",
        compliance_status="rejected",
        salary_transparency_status="unknown",
        remote_source_flag=False,
        first_seen_at="2026-01-04T10:00:00+00:00",
    )

    db_factory.create_job(
        company_static["company_id"],
        job_id="static-job",
        title="Office Job",
        company_name=company_static["legal_name"],
        status="active",
        compliance_status="approved",
        salary_transparency_status="unknown",
        remote_source_flag=True,
        first_seen_at="2026-01-05T10:00:00+00:00",
    )

    assert update_company_job_stats_bulk() == 2
    assert update_company_remote_posture_bulk() == 1
    assert update_company_signal_scores_bulk() == 2
    assert update_company_job_stats_bulk() == 0
    assert update_company_remote_posture_bulk() == 0
    assert update_company_signal_scores_bulk() == 0

    with db_factory.engine.begin() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT legal_name, remote_posture, approved_jobs_count, rejected_jobs_count, total_jobs_count, signal_score
                FROM companies
                ORDER BY legal_name
            """)
            )
            .mappings()
            .all()
        )

    assert rows == [
        {
            "legal_name": "Remote Co",
            "remote_posture": "REMOTE_FRIENDLY",
            "approved_jobs_count": 3,
            "rejected_jobs_count": 1,
            "total_jobs_count": 4,
            "signal_score": 88,
        },
        {
            "legal_name": "Static Co",
            "remote_posture": "UNKNOWN",
            "approved_jobs_count": 1,
            "rejected_jobs_count": 0,
            "total_jobs_count": 1,
            "signal_score": 15,
        },
    ]
