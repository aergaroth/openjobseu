from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from storage.repositories.lifecycle_repository import (
    activate_new_jobs_due_to_lifecycle,
    expire_jobs_due_to_lifecycle,
    mark_reposts_due_to_lifecycle,
    reactivate_stale_jobs_due_to_lifecycle,
    stale_active_jobs_due_to_lifecycle,
)


def test_lifecycle_transitions_update_expected_jobs(db_factory):
    company = db_factory.create_company(legal_name="Lifecycle Co")
    now = datetime.now(timezone.utc)

    db_factory.create_job(
        company["company_id"],
        job_id="job-expire-failures",
        status="active",
        verification_failures=3,
        availability_status="active",
    )
    db_factory.create_job(
        company["company_id"],
        job_id="job-expire-old",
        status="stale",
        verification_failures=0,
        availability_status="active",
        last_verified_at=now - timedelta(days=31),
    )
    db_factory.create_job(
        company["company_id"],
        job_id="job-stale",
        status="active",
        verification_failures=0,
        availability_status="active",
        last_verified_at=now - timedelta(days=8),
    )
    db_factory.create_job(
        company["company_id"],
        job_id="job-activate-new",
        status="new",
        verification_failures=0,
        first_seen_at=now - timedelta(hours=25),
    )
    db_factory.create_job(
        company["company_id"],
        job_id="job-reactivate",
        status="stale",
        verification_failures=0,
        availability_status="active",
        last_verified_at=now - timedelta(days=2),
    )
    db_factory.create_job(
        company["company_id"],
        job_id="job-untouched",
        status="active",
        verification_failures=0,
        availability_status="active",
        last_verified_at=now - timedelta(days=1),
    )

    assert expire_jobs_due_to_lifecycle() == 2
    assert stale_active_jobs_due_to_lifecycle() == 1
    assert activate_new_jobs_due_to_lifecycle() == 1
    assert reactivate_stale_jobs_due_to_lifecycle() == 1

    with db_factory.engine.begin() as conn:
        statuses = dict(conn.execute(text("SELECT job_id, status FROM jobs")).fetchall())

    assert statuses["job-expire-failures"] == "expired"
    assert statuses["job-expire-old"] == "expired"
    assert statuses["job-stale"] == "stale"
    assert statuses["job-activate-new"] == "active"
    assert statuses["job-reactivate"] == "active"
    assert statuses["job-untouched"] == "active"


def test_mark_reposts_due_to_lifecycle_clears_stale_repost_flags_and_is_idempotent(db_factory):
    company = db_factory.create_company(legal_name="Repost Co")
    now = datetime.now(timezone.utc)
    db_factory.create_job(
        company["company_id"],
        job_id="job-stale-flag",
        title="Backend Engineer",
        company_name="Repost Co",
        job_fingerprint="fp-unique",
        first_seen_at=now - timedelta(days=6),
        last_seen_at=now - timedelta(days=5),
        is_repost=True,
        repost_count=1,
    )

    assert mark_reposts_due_to_lifecycle(days_threshold=30) == 1
    assert mark_reposts_due_to_lifecycle(days_threshold=30) == 0

    with db_factory.engine.begin() as conn:
        row = (
            conn.execute(
                text("""
                SELECT job_id, is_repost, repost_count
                FROM jobs
                WHERE job_id = 'job-stale-flag'
            """)
            )
            .mappings()
            .one()
        )

    assert row == {"job_id": "job-stale-flag", "is_repost": False, "repost_count": 0}
