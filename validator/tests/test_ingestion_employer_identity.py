from datetime import datetime, timezone

from app.domain.classification.enums import GeoClass, RemoteClass
from app.domain.jobs.identity import (
    compute_job_fingerprint,
    compute_job_uid,
    compute_schema_hash,
)
from app.workers.ingestion import employer


class _NoopTx:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


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

    monkeypatch.setattr(employer, "get_adapter", lambda _provider: _FakeAdapter)
    monkeypatch.setattr(employer, "get_engine", lambda: _NoopEngine())

    def _fake_apply_policy(job, source):
        call_order.append("apply_policy")
        assert source == "greenhouse:acme"
        assert job["job_uid"] == compute_job_uid(
            "company-1",
            normalize_output["title"],
            normalize_output["remote_scope"],
            normalize_output["description"],
        )
        assert job["job_fingerprint"] == compute_job_fingerprint(
            normalize_output["description"],
            title=normalize_output["title"],
            location=normalize_output["remote_scope"],
            company_id="company-1",
            company_name=normalize_output["company_name"],
        )
        assert job["source_schema_hash"] == compute_schema_hash(raw_job)
        job["_compliance"] = {
            "policy_version": "v9",
            "policy_reason": None,
            "remote_model": RemoteClass.REMOTE_ONLY.value,
            "geo_class": GeoClass.EU_EXPLICIT.value,
        }
        return job, None

    monkeypatch.setattr(employer, "apply_policy", _fake_apply_policy)

    def _fake_upsert(job, conn=None, *, company_id=None):
        call_order.append("upsert")
        assert conn is not None
        assert company_id == "company-1"
        persisted_jobs.append(dict(job))
        return job["job_id"]

    monkeypatch.setattr(employer, "upsert_job", _fake_upsert)
    monkeypatch.setattr(
        employer,
        "insert_compliance_report",
        lambda *args, **kwargs: call_order.append("insert_report"),
    )
    monkeypatch.setattr(
        employer,
        "_mark_ats_synced",
        lambda _conn, company_ats_id: sync_markers.append(company_ats_id),
    )

    result = employer.ingest_company(company)

    assert result["fetched"] == 1
    assert result["normalized_count"] == 1
    assert result["accepted"] == 1
    assert result["skipped"] == 0
    assert call_order == ["normalize", "apply_policy", "upsert", "insert_report"]
    assert len(persisted_jobs) == 1
    assert persisted_jobs[0]["job_uid"]
    assert persisted_jobs[0]["job_fingerprint"]
    assert persisted_jobs[0]["source_schema_hash"]
    assert persisted_jobs[0]["policy_version"] == "v9"
    assert sync_markers == ["company-ats-1"]
