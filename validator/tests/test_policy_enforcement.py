import sys
from types import SimpleNamespace

import pytest

sys.modules.setdefault("feedparser", SimpleNamespace(parse=lambda *_args, **_kwargs: None))

from app.workers.ingestion import remoteok, remotive, weworkremotely
from app.workers.policy import v1
from app.workers.policy.v1 import apply_policy_v1


class _NoopTx:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


class _NoopEngine:
    def begin(self):
        return _NoopTx()


def test_apply_policy_v1_flags_job_without_rejecting():
    job = {
        "job_id": "remoteok:1",
        "title": "Senior PM",
        "description": "100% remote but must be based in the US",
    }

    assert apply_policy_v1(job, source="remoteok") == (job, "geo_restriction")
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
        v1,
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
def test_ingestion_persists_policy_flagged_jobs(
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
    seen_connections = []

    def _fake_upsert(job, **kwargs):
        persisted.append(job)
        seen_connections.append(kwargs.get("conn"))

    # monkeypatch.setattr(module, "init_db", lambda: None)
    monkeypatch.setattr(module, adapter_attr, FakeAdapter)
    monkeypatch.setattr(module, normalize_attr, lambda _: rejected_job)
    monkeypatch.setattr(module, "get_engine", lambda: _NoopEngine())
    monkeypatch.setattr(module, "upsert_job", _fake_upsert)

    result = getattr(module, runner_name)()

    assert len(persisted) == 1
    assert len(seen_connections) == 1
    assert seen_connections[0] is not None
    assert result["metrics"]["fetched_count"] == 1
    assert result["metrics"]["normalized_count"] == 1
    assert result["metrics"]["accepted_count"] == 1
    assert result["metrics"]["rejected_policy_count"] == 1
    assert result["metrics"]["policy_rejected_total"] == 1
    assert result["metrics"]["policy_rejected_by_reason"]["non_remote"] == 0
    assert result["metrics"]["policy_rejected_by_reason"]["geo_restriction"] == 1
    assert result["metrics"]["raw_count"] == 1
    assert result["metrics"]["persisted_count"] == 1
    assert result["metrics"]["skipped_count"] == 0


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
    seen_connections = []

    def _fake_upsert(job, **kwargs):
        persisted.append(job)
        seen_connections.append(kwargs.get("conn"))

    # monkeypatch.setattr(remoteok, "init_db", lambda: None)
    monkeypatch.setattr(remoteok, "RemoteOkApiAdapter", FakeAdapter)
    monkeypatch.setattr(
        remoteok,
        "normalize_remoteok_job",
        lambda raw: normalized_jobs[raw["id"]],
    )
    monkeypatch.setattr(remoteok, "get_engine", lambda: _NoopEngine())
    monkeypatch.setattr(remoteok, "upsert_job", _fake_upsert)
    monkeypatch.setattr(remoteok, "log_ingestion", lambda **kwargs: log_calls.append(kwargs))

    result = remoteok.run_remoteok_ingestion()

    assert not any(call.get("phase") == "start" for call in log_calls)
    summary_calls = [call for call in log_calls if call.get("phase") == "ingestion_summary"]
    assert len(summary_calls) == 1

    summary = summary_calls[0]
    assert summary["source"] == "remoteok"
    assert summary["fetched"] == 3
    assert summary["normalized"] == 2
    assert summary["accepted"] == 2
    assert summary["rejected_policy"] == 1
    assert summary["rejected_non_remote"] == 0
    assert summary["rejected_geo_restriction"] == 1
    assert summary["duration_ms"] >= 0

    assert len(persisted) == 2
    assert len(seen_connections) == 2
    assert all(conn is not None for conn in seen_connections)
    assert len({id(conn) for conn in seen_connections}) == 1
    assert result["metrics"]["fetched_count"] == 3
    assert result["metrics"]["normalized_count"] == 2
    assert result["metrics"]["accepted_count"] == 2
    assert result["metrics"]["rejected_policy_count"] == 1
    assert result["metrics"]["policy_rejected_total"] == 1
    assert result["metrics"]["policy_rejected_by_reason"]["non_remote"] == 0
    assert result["metrics"]["policy_rejected_by_reason"]["geo_restriction"] == 1
