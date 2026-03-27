import json

from sqlalchemy import text

from storage.repositories.compliance_repository import (
    count_jobs_missing_compliance,
    get_jobs_for_compliance_resolution,
    insert_compliance_report,
    insert_compliance_reports,
    update_job_compliance_resolution,
    update_jobs_compliance_resolution,
)


def _as_json(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def test_insert_compliance_report_upserts_and_serializes_json(db_factory):
    company = db_factory.create_company()
    db_factory.create_job(
        company["company_id"],
        job_id="job-compliance-1",
        job_uid="uid-1",
        remote_class="REMOTE_ONLY",
        geo_class="EU_REGION",
    )

    with db_factory.engine.begin() as conn:
        insert_compliance_report(
            conn,
            job_id="job-compliance-1",
            job_uid="uid-1",
            policy_version="v1",
            remote_class="REMOTE_ONLY",
            geo_class="EU_REGION",
            hard_geo_flag=False,
            base_score=90,
            penalties={"geo": -5},
            bonuses={"salary": 10},
            final_score=95,
            final_status="approved",
            decision_vector={"remote": True},
        )
        insert_compliance_report(
            conn,
            job_id="job-compliance-1",
            job_uid="uid-1",
            policy_version="v1",
            remote_class="REMOTE_ONLY",
            geo_class="EU_REGION",
            hard_geo_flag=True,
            base_score=80,
            penalties={"geo": -10},
            bonuses={"salary": 5},
            final_score=75,
            final_status="rejected",
            decision_vector={"remote": False},
        )
        row = (
            conn.execute(
                text("""
                SELECT hard_geo_flag, base_score, penalties, bonuses, final_score, final_status, decision_vector
                FROM compliance_reports
                WHERE job_uid = 'uid-1' AND policy_version = 'v1'
            """)
            )
            .mappings()
            .one()
        )

    assert row["hard_geo_flag"] is True
    assert row["base_score"] == 80
    assert _as_json(row["penalties"]) == {"geo": -10}
    assert _as_json(row["bonuses"]) == {"salary": 5}
    assert row["final_score"] == 75
    assert row["final_status"] == "rejected"
    assert _as_json(row["decision_vector"]) == {"remote": False}


def test_bulk_compliance_helpers_cover_insert_count_fetch_and_update(db_factory):
    company = db_factory.create_company()
    db_factory.create_job(
        company["company_id"],
        job_id="job-missing",
        job_uid="uid-missing",
        remote_class="UNKNOWN",
        geo_class="UNKNOWN",
        compliance_status=None,
        compliance_score=None,
    )
    db_factory.create_job(
        company["company_id"],
        job_id="job-complete",
        job_uid="uid-complete",
        remote_class="REMOTE_ONLY",
        geo_class="EU_REGION",
        compliance_status="approved",
        compliance_score=90,
    )

    with db_factory.engine.begin() as conn:
        insert_compliance_reports(
            conn,
            [
                {
                    "job_id": "job-missing",
                    "job_uid": "uid-missing",
                    "policy_version": "v2",
                    "remote_class": "UNKNOWN",
                    "geo_class": "UNKNOWN",
                    "hard_geo_flag": False,
                    "base_score": 50,
                    "penalties": {"missing": 1},
                    "bonuses": None,
                    "final_score": 50,
                    "final_status": "review",
                    "decision_vector": {"source": "bulk"},
                }
            ],
        )
        update_job_compliance_resolution("job-missing", "approved", 81, conn=conn)
        update_jobs_compliance_resolution(
            [{"job_id": "job-complete", "compliance_status": "rejected", "compliance_score": 10}],
            conn=conn,
        )

    assert count_jobs_missing_compliance() == 0

    only_missing = get_jobs_for_compliance_resolution(limit=10, only_missing=True)
    all_jobs = get_jobs_for_compliance_resolution(limit=10, only_missing=False)

    assert only_missing == []
    assert {job["job_id"] for job in all_jobs} == {"job-missing", "job-complete"}

    with db_factory.engine.begin() as conn:
        row = (
            conn.execute(
                text("""
                SELECT compliance_status, compliance_score
                FROM jobs
                WHERE job_id = 'job-complete'
            """)
            )
            .mappings()
            .one()
        )
        report = (
            conn.execute(
                text("""
                SELECT penalties, decision_vector
                FROM compliance_reports
                WHERE job_uid = 'uid-missing' AND policy_version = 'v2'
            """)
            )
            .mappings()
            .one()
        )

    assert row == {"compliance_status": "rejected", "compliance_score": 10}
    assert _as_json(report["penalties"]) == {"missing": 1}
    assert _as_json(report["decision_vector"]) == {"source": "bulk"}
