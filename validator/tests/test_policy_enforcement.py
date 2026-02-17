import sys
from types import SimpleNamespace

import pytest

sys.modules.setdefault("feedparser", SimpleNamespace(parse=lambda *_args, **_kwargs: None))

from app.workers.ingestion import remoteok, remotive, weworkremotely
from app.workers.policy import enforcement
from app.workers.policy.enforcement import apply_policy_v1


def test_apply_policy_v1_rejects_job():
    job = {
        "job_id": "remoteok:1",
        "title": "Senior PM",
        "description": "100% remote but must be based in the US",
    }

    assert apply_policy_v1(job, source="remoteok") == (None, "geo_restriction")
    assert job["_compliance"]["policy_version"] == "v1"
    assert job["_compliance"]["policy_reason"] == "geo_restriction"
    assert job["_compliance"]["remote_model"] == "remote_but_geo_restricted"


def test_apply_policy_v1_accepts_job():
    job = {
        "job_id": "remoteok:2",
        "title": "Backend Engineer",
        "description": "Fully remote role in Europe",
    }

    assert apply_policy_v1(job, source="remoteok") == (job, None)
    assert job["_compliance"]["policy_version"] == "v1"
    assert job["_compliance"]["policy_reason"] is None
    assert job["_compliance"]["remote_model"] == "remote_only"


def test_apply_policy_v1_calls_classifier_safely_when_fields_missing(monkeypatch):
    calls = []

    monkeypatch.setattr(
        enforcement,
        "classify_remote_model",
        lambda title, description: calls.append((title, description))
        or {"remote_model": "unknown"},
    )

    job = {
        "job_id": "remoteok:3",
    }

    assert apply_policy_v1(job, source="remoteok") == (job, None)
    assert calls == [("", "")]
    assert job["_compliance"] == {
        "policy_version": "v1",
        "policy_reason": None,
        "remote_model": "unknown",
    }


def test_apply_policy_v1_logs_policy_audit_on_reject(monkeypatch):
    calls = []

    monkeypatch.setattr(
        enforcement.audit_logger,
        "info",
        lambda message, extra=None: calls.append({"message": message, "extra": extra or {}}),
    )

    job = {
        "job_id": "remoteok:1",
        "title": "Senior PM",
        "description": "100% remote but must be based in the US",
    }

    assert apply_policy_v1(job, source="remoteok") == (None, "geo_restriction")
    assert len(calls) == 1
    assert calls[0]["message"] == "policy_reject[remoteok]"
    assert calls[0]["extra"] == {
        "component": "policy",
        "job_id": "remoteok:1",
        "reason": "geo_restriction",
        "policy_version": "v1",
    }


def test_apply_policy_v1_does_not_log_policy_audit_on_accept(monkeypatch):
    calls = []

    monkeypatch.setattr(
        enforcement.audit_logger,
        "info",
        lambda message, extra=None: calls.append({"message": message, "extra": extra or {}}),
    )

    job = {
        "job_id": "remoteok:2",
        "title": "Backend Engineer",
        "description": "Fully remote role in Europe",
    }

    assert apply_policy_v1(job, source="remoteok") == (job, None)
    assert calls == []


@pytest.mark.parametrize(
    "module,adapter_attr,normalize_attr,runner_name",
    [
        (remoteok, "RemoteOkApiAdapter", "normalize_remoteok_job", "run_remoteok_ingestion"),
        (remotive, "RemotiveApiAdapter", "normalize_remotive_job", "run_remotive_ingestion"),
        (
            weworkremotely,
            "WeWorkRemotelyRssAdapter",
            "normalize_weworkremotely_job",
            "run_weworkremotely_ingestion",
        ),
    ],
)
def test_ingestion_skips_policy_rejected_jobs(
    monkeypatch,
    module,
    adapter_attr,
    normalize_attr,
    runner_name,
):
    class FakeAdapter:
        def fetch(self):
            return [{"id": "raw-1"}]

    rejected_job = {
        "job_id": "x:1",
        "title": "Senior PM",
        "description": "100% remote but must be based in the US",
    }

    persisted = []

    # monkeypatch.setattr(module, "init_db", lambda: None)
    monkeypatch.setattr(module, adapter_attr, FakeAdapter)
    monkeypatch.setattr(module, normalize_attr, lambda _: rejected_job)
    monkeypatch.setattr(module, "upsert_job", lambda job: persisted.append(job))

    result = getattr(module, runner_name)()

    assert persisted == []
    assert result["metrics"]["fetched_count"] == 1
    assert result["metrics"]["normalized_count"] == 1
    assert result["metrics"]["accepted_count"] == 0
    assert result["metrics"]["rejected_policy_count"] == 1
    assert result["metrics"]["policy_rejected_total"] == 1
    assert result["metrics"]["policy_rejected_by_reason"]["non_remote"] == 0
    assert result["metrics"]["policy_rejected_by_reason"]["geo_restriction"] == 1
    assert result["metrics"]["raw_count"] == 1
    assert result["metrics"]["persisted_count"] == 0
    assert result["metrics"]["skipped_count"] == 1


def test_ingestion_emits_single_summary_log(monkeypatch):
    class FakeAdapter:
        def fetch(self):
            return [{"id": "raw-1"}, {"id": "raw-2"}, {"id": "raw-3"}]

    normalized_jobs = {
        "raw-1": None,
        "raw-2": {
            "job_id": "remoteok:2",
            "title": "Senior PM",
            "description": "Remote but must be based in the US",
        },
        "raw-3": {
            "job_id": "remoteok:3",
            "title": "Backend Engineer",
            "description": "Fully remote role in Europe",
        },
    }

    log_calls = []
    persisted = []

    # monkeypatch.setattr(remoteok, "init_db", lambda: None)
    monkeypatch.setattr(remoteok, "RemoteOkApiAdapter", FakeAdapter)
    monkeypatch.setattr(
        remoteok,
        "normalize_remoteok_job",
        lambda raw: normalized_jobs[raw["id"]],
    )
    monkeypatch.setattr(remoteok, "upsert_job", lambda job: persisted.append(job))
    monkeypatch.setattr(remoteok, "log_ingestion", lambda **kwargs: log_calls.append(kwargs))

    result = remoteok.run_remoteok_ingestion()

    assert not any(call.get("phase") == "start" for call in log_calls)
    summary_calls = [call for call in log_calls if call.get("phase") == "ingestion_summary"]
    assert len(summary_calls) == 1

    summary = summary_calls[0]
    assert summary["source"] == "remoteok"
    assert summary["fetched"] == 3
    assert summary["normalized"] == 2
    assert summary["accepted"] == 1
    assert summary["rejected_policy"] == 1
    assert summary["rejected_non_remote"] == 0
    assert summary["rejected_geo_restriction"] == 1
    assert summary["duration_ms"] >= 0

    assert len(persisted) == 1
    assert result["metrics"]["fetched_count"] == 3
    assert result["metrics"]["normalized_count"] == 2
    assert result["metrics"]["accepted_count"] == 1
    assert result["metrics"]["rejected_policy_count"] == 1
    assert result["metrics"]["policy_rejected_total"] == 1
    assert result["metrics"]["policy_rejected_by_reason"]["non_remote"] == 0
    assert result["metrics"]["policy_rejected_by_reason"]["geo_restriction"] == 1
