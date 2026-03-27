from datetime import datetime, timedelta, timezone
import uuid

from storage.repositories.system_repository import get_system_metrics


def test_get_system_metrics_returns_zero_defaults_for_empty_database():
    metrics = get_system_metrics()

    assert metrics == {
        "jobs_total": 0,
        "jobs_24h": 0,
        "companies_total": 0,
        "companies_24h": 0,
        "company_ats_total": 0,
        "company_ats_24h": 0,
        "last_tick_at": None,
    }


def test_get_system_metrics_counts_recent_records_and_formats_timestamp(db_factory):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=3)
    company_recent = db_factory.create_company(legal_name="Recent Co", created_at=now, updated_at=now)
    company_old = db_factory.create_company(legal_name="Old Co", created_at=old, updated_at=old)
    db_factory.create_ats(
        company_recent["company_id"], company_ats_id=str(uuid.uuid4()), created_at=now, updated_at=now
    )
    db_factory.create_ats(company_old["company_id"], company_ats_id=str(uuid.uuid4()), created_at=old, updated_at=old)
    db_factory.create_job(
        company_recent["company_id"],
        job_id="job-recent",
        first_seen_at=now,
        last_seen_at=now,
    )
    db_factory.create_job(
        company_old["company_id"],
        job_id="job-old",
        first_seen_at=old,
        last_seen_at=old,
    )

    metrics = get_system_metrics()

    assert metrics["jobs_total"] == 2
    assert metrics["jobs_24h"] == 1
    assert metrics["companies_total"] == 2
    assert metrics["companies_24h"] == 1
    assert metrics["company_ats_total"] == 2
    assert metrics["company_ats_24h"] == 1
    assert metrics["last_tick_at"] is not None
    assert metrics["last_tick_at"].startswith(now.date().isoformat())
