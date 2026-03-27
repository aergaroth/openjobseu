from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from storage.repositories.availability_repository import (
    get_jobs_for_verification,
    update_job_availability,
    update_jobs_availability,
)


def test_get_jobs_for_verification_returns_only_due_active_or_stale_jobs(db_factory):
    company = db_factory.create_company()
    now = datetime.now(timezone.utc)
    db_factory.create_job(
        company["company_id"],
        job_id="job-active-due",
        status="active",
        last_verified_at=now - timedelta(hours=7),
        verification_failures=1,
    )
    db_factory.create_job(
        company["company_id"],
        job_id="job-stale-missing",
        status="stale",
        last_verified_at=None,
        verification_failures=0,
    )
    db_factory.create_job(
        company["company_id"],
        job_id="job-fresh",
        status="active",
        last_verified_at=now - timedelta(hours=2),
        verification_failures=0,
    )
    db_factory.create_job(
        company["company_id"],
        job_id="job-expired",
        status="expired",
        last_verified_at=now - timedelta(days=2),
        verification_failures=3,
    )

    jobs = get_jobs_for_verification(limit=10)

    assert [job["job_id"] for job in jobs] == ["job-stale-missing", "job-active-due"]


def test_update_job_availability_resets_or_increments_failures(db_factory):
    company = db_factory.create_company()
    verified_at = datetime.now(timezone.utc)
    db_factory.create_job(
        company["company_id"],
        job_id="job-availability",
        status="active",
        verification_failures=2,
    )

    with db_factory.engine.begin() as conn:
        update_job_availability(
            "job-availability",
            "expired",
            verified_at=verified_at,
            failure=True,
            conn=conn,
        )
        failed_row = (
            conn.execute(
                text("""
                SELECT availability_status, verification_failures
                FROM jobs
                WHERE job_id = 'job-availability'
            """)
            )
            .mappings()
            .one()
        )
        assert failed_row["availability_status"] == "expired"
        assert failed_row["verification_failures"] == 3

        update_job_availability(
            "job-availability",
            "active",
            verified_at=verified_at + timedelta(minutes=5),
            failure=False,
            conn=conn,
        )

    final_row = db_factory.get_job("job-availability")
    assert final_row["availability_status"] == "active"
    assert final_row["verification_failures"] == 0
    assert final_row["last_verified_at"] is not None


def test_update_jobs_availability_supports_bulk_and_empty_input(db_factory):
    company = db_factory.create_company()
    db_factory.create_job(company["company_id"], job_id="job-bulk-1", status="active", verification_failures=0)
    db_factory.create_job(company["company_id"], job_id="job-bulk-2", status="stale", verification_failures=4)
    verified_at = datetime.now(timezone.utc)

    with db_factory.engine.begin() as conn:
        update_jobs_availability([], conn=conn)
        update_jobs_availability(
            [
                {
                    "job_id": "job-bulk-1",
                    "availability_status": "active",
                    "verified_at": verified_at,
                    "failure": False,
                },
                {
                    "job_id": "job-bulk-2",
                    "availability_status": "unreachable",
                    "verified_at": verified_at,
                    "failure": True,
                },
            ],
            conn=conn,
        )
        rows = (
            conn.execute(
                text("""
                SELECT job_id, availability_status, verification_failures
                FROM jobs
                WHERE job_id IN ('job-bulk-1', 'job-bulk-2')
                ORDER BY job_id
            """)
            )
            .mappings()
            .all()
        )

    assert rows == [
        {"job_id": "job-bulk-1", "availability_status": "active", "verification_failures": 0},
        {"job_id": "job-bulk-2", "availability_status": "unreachable", "verification_failures": 5},
    ]
