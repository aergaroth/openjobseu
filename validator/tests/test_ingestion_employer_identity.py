from datetime import datetime, timezone
from uuid import uuid4

from app.domain.jobs.enums import GeoClass, RemoteClass
from app.domain.jobs.identity import (
    compute_job_fingerprint,
    compute_job_uid,
)
from app.workers.ingestion import employer, process_loop


class _NoopTx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def begin_nested(self):
        return self


class _NoopEngine:
    def begin(self):
        return _NoopTx()


def test_ingest_company_computes_identity_before_policy_and_persist(monkeypatch):
    last_sync_at = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    company = {
        "company_ats_id": "company-ats-1",
        "company_id": "company-1",
        "ats_provider": "greenhouse",
        "ats_slug": "acme",
        "last_sync_at": last_sync_at,
    }
    raw_job = {
        "id": 123,
        "title": "Senior Backend Engineer",
        "description": "Build APIs for EU clients.",
        "location": {"name": "Poland"},
        "absolute_url": "https://example.com/jobs/123",
    }
    normalize_output = {
        "job_id": "greenhouse:acme:123",
        "source": "greenhouse:acme",
        "source_job_id": "123",
        "source_url": "https://example.com/jobs/123",
        "title": "Senior Backend Engineer",
        "company_name": "Acme",
        "description": "Build APIs for EU clients.",
        "remote_source_flag": True,
        "remote_scope": "Poland",
        "status": "new",
        "first_seen_at": "2026-01-01T00:00:00+00:00",
    }

    call_order: list[str] = []
    persisted_jobs: list[dict] = []
    sync_markers: list[str] = []

    class _FakeAdapter:
        active = True

        def fetch(self, _company, updated_since=None):
            assert updated_since == last_sync_at
            return [raw_job]

        def normalize(self, _raw_job):
            call_order.append("normalize")
            return dict(normalize_output)

    monkeypatch.setattr(employer, "get_adapter", lambda _provider: _FakeAdapter())
    monkeypatch.setattr(employer, "get_engine", lambda: _NoopEngine())

    def _fake_process_ingested_job(job, source):
        call_order.append("apply_policy")
        assert source == "greenhouse"
        assert job["company_id"] == "company-1"

        # Identity is now computed inside process_ingested_job
        # but for this test we'll mock its behavior
        job["job_uid"] = compute_job_uid(
            job["company_id"],
            job["title"],
            job["remote_scope"],
        )
        job["job_fingerprint"] = compute_job_fingerprint(
            job["description"],
            title=job["title"],
            location=job["remote_scope"],
            company_id=job["company_id"],
            company_name=job["company_name"],
        )
        # source_schema_hash is set by worker before call

        job["_compliance"] = {
            "policy_version": "v9",
            "policy_reason": None,
            "remote_model": RemoteClass.REMOTE_ONLY.value,
            "geo_class": GeoClass.EU_EXPLICIT.value,
            "compliance_status": "approved",
            "compliance_score": 100,
            "decision_trace": [],
        }
        job["policy_version"] = "v9"
        job["compliance_status"] = "approved"
        job["compliance_score"] = 100

        report = {
            "job_id": None,
            "job_uid": job["job_uid"],
            "policy_version": "v9",
            "remote_class": job["_compliance"]["remote_model"],
            "geo_class": job["_compliance"]["geo_class"],
            "hard_geo_flag": False,
            "base_score": 100,
            "final_score": 100,
            "final_status": "approved",
            "decision_vector": [],
            "policy_reason": None,
        }
        return job, report

    monkeypatch.setattr(process_loop, "process_ingested_job", _fake_process_ingested_job)

    def _fake_upsert(jobs, conn, *, company_id=None, source=None):
        call_order.append("upsert")
        assert conn is not None
        assert company_id == "company-1"
        for job in jobs:
            persisted_jobs.append(dict(job))
        return [job["job_id"] for job in jobs]

    monkeypatch.setattr(process_loop, "bulk_upsert_jobs", _fake_upsert)
    monkeypatch.setattr(
        process_loop,
        "insert_compliance_reports",
        lambda conn, reports: call_order.append("insert_reports"),
    )
    monkeypatch.setattr(
        process_loop,
        "insert_salary_parsing_cases",
        lambda conn, cases: None,
    )
    monkeypatch.setattr(
        employer,
        "mark_ats_synced",
        lambda _conn, company_ats_id, success=True: sync_markers.append(company_ats_id),
    )

    result = employer.ingest_company(company)

    assert result["fetched"] == 1
    assert result["normalized_count"] == 1
    assert result["accepted"] == 1
    assert result["skipped"] == 0
    assert call_order == ["normalize", "apply_policy", "upsert", "insert_reports"]
    assert len(persisted_jobs) == 1
    assert persisted_jobs[0]["job_uid"]
    assert persisted_jobs[0]["job_fingerprint"]
    assert persisted_jobs[0]["source_schema_hash"]
    assert persisted_jobs[0]["policy_version"] == "v9"
    assert sync_markers == ["company-ats-1"]


def test_ingest_company_accepts_uuid_company_identifiers(monkeypatch):
    last_sync_at = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    company_uuid = uuid4()
    company_ats_uuid = uuid4()
    company = {
        "company_ats_id": company_ats_uuid,
        "company_id": company_uuid,
        "ats_provider": "greenhouse",
        "ats_slug": "acme",
        "last_sync_at": last_sync_at,
    }
    raw_job = {
        "id": 456,
        "title": "Platform Engineer",
        "description": "Remote role in EU timezone.",
        "location": {"name": "Europe"},
        "absolute_url": "https://example.com/jobs/456",
    }
    normalize_output = {
        "job_id": "greenhouse:acme:456",
        "source": "greenhouse:acme",
        "source_job_id": "456",
        "source_url": "https://example.com/jobs/456",
        "title": "Platform Engineer",
        "company_name": "Acme",
        "description": "Remote role in EU timezone.",
        "remote_source_flag": True,
        "remote_scope": "Europe",
        "status": "new",
        "first_seen_at": "2026-01-01T00:00:00+00:00",
    }

    persisted_jobs: list[dict] = []
    sync_markers: list[object] = []

    class _FakeAdapter:
        active = True

        def fetch(self, _company, updated_since=None):
            assert updated_since == last_sync_at
            return [raw_job]

        def normalize(self, _raw_job):
            return dict(normalize_output)

    monkeypatch.setattr(employer, "get_adapter", lambda _provider: _FakeAdapter())
    monkeypatch.setattr(employer, "get_engine", lambda: _NoopEngine())

    def _fake_process_ingested_job(job, source):
        assert source == "greenhouse"
        assert isinstance(job["company_id"], str)
        assert job["company_id"] == str(company_uuid)

        job["job_uid"] = compute_job_uid(
            job["company_id"],
            job["title"],
            job["remote_scope"],
        )
        job["job_fingerprint"] = compute_job_fingerprint(
            job["description"],
            title=job["title"],
            location=job["remote_scope"],
            company_id=job["company_id"],
            company_name=job["company_name"],
        )

        job["_compliance"] = {
            "policy_version": "v9",
            "policy_reason": None,
            "remote_model": RemoteClass.REMOTE_ONLY.value,
            "geo_class": GeoClass.EU_EXPLICIT.value,
            "compliance_status": "approved",
            "compliance_score": 100,
            "decision_trace": [],
        }
        report = {
            "job_id": None,
            "job_uid": job["job_uid"],
            "policy_version": "v9",
            "remote_class": job["_compliance"]["remote_model"],
            "geo_class": job["_compliance"]["geo_class"],
            "hard_geo_flag": False,
            "base_score": 100,
            "final_score": 100,
            "final_status": "approved",
            "decision_vector": [],
            "policy_reason": None,
        }
        return job, report

    monkeypatch.setattr(process_loop, "process_ingested_job", _fake_process_ingested_job)
    monkeypatch.setattr(
        process_loop,
        "insert_compliance_reports",
        lambda conn, reports: None,
    )
    monkeypatch.setattr(
        process_loop,
        "insert_salary_parsing_cases",
        lambda conn, cases: None,
    )
    monkeypatch.setattr(
        process_loop,
        "bulk_upsert_jobs",
        lambda jobs, conn, *, company_id=None, source=None: [
            persisted_jobs.append(dict(j)) or j["job_id"] for j in jobs
        ],
    )
    monkeypatch.setattr(
        employer,
        "mark_ats_synced",
        lambda _conn, company_ats_id, success=True: sync_markers.append(company_ats_id),
    )

    result = employer.ingest_company(company)

    assert result["accepted"] == 1
    assert len(persisted_jobs) == 1
    assert persisted_jobs[0]["job_uid"]
    assert persisted_jobs[0]["job_fingerprint"]
    assert sync_markers == [company_ats_uuid]


def test_ingest_company_rejected_job_does_not_insert_compliance_report_without_job_id(
    monkeypatch,
):
    last_sync_at = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    company = {
        "company_ats_id": "company-ats-1",
        "company_id": "company-1",
        "ats_provider": "greenhouse",
        "ats_slug": "acme",
        "last_sync_at": last_sync_at,
    }
    raw_job = {
        "id": 789,
        "title": "US-only role",
        "description": "Remote only in US timezones",
        "location": {"name": "United States"},
        "absolute_url": "https://example.com/jobs/789",
    }
    normalize_output = {
        "job_id": "greenhouse:acme:789",
        "source": "greenhouse:acme",
        "source_job_id": "789",
        "source_url": "https://example.com/jobs/789",
        "title": "US-only role",
        "company_name": "Acme",
        "description": "Remote only in US timezones",
        "remote_source_flag": True,
        "remote_scope": "US",
        "status": "new",
        "first_seen_at": "2026-01-01T00:00:00+00:00",
    }

    upsert_calls: list[dict] = []
    report_calls: list[dict] = []

    class _FakeAdapter:
        active = True

        def fetch(self, _company, updated_since=None):
            assert updated_since == last_sync_at
            return [raw_job]

        def normalize(self, _raw_job):
            return dict(normalize_output)

    monkeypatch.setattr(employer, "get_adapter", lambda _provider: _FakeAdapter())
    monkeypatch.setattr(employer, "get_engine", lambda: _NoopEngine())

    def _fake_process_ingested_job(job, source):
        assert source == "greenhouse"
        report = {
            "job_id": None,
            "job_uid": "uid-rejected-1",
            "policy_version": "v3",
            "remote_class": RemoteClass.REMOTE_REGION_LOCKED.value,
            "geo_class": GeoClass.NON_EU.value,
            "hard_geo_flag": False,
            "base_score": 0,
            "final_score": 0,
            "final_status": "rejected",
            "decision_vector": [],
            "policy_reason": "geo_restriction",
        }
        return None, report

    monkeypatch.setattr(process_loop, "process_ingested_job", _fake_process_ingested_job)
    monkeypatch.setattr(
        process_loop,
        "bulk_upsert_jobs",
        lambda jobs, conn, *, company_id=None, source=None: [
            upsert_calls.append(dict(j)) or j.get("job_id", "job-x") for j in jobs
        ],
    )
    monkeypatch.setattr(
        process_loop,
        "insert_compliance_reports",
        lambda conn, reports: report_calls.extend(reports),
    )
    monkeypatch.setattr(
        process_loop,
        "insert_salary_parsing_cases",
        lambda conn, cases: None,
    )
    monkeypatch.setattr(employer, "mark_ats_synced", lambda _conn, _company_ats_id, success=True: None)

    result = employer.ingest_company(company)

    assert result["accepted"] == 0
    assert result["skipped"] == 1
    assert upsert_calls == []
    assert report_calls == []
