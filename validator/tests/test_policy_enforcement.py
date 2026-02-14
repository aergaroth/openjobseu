import sys
from types import SimpleNamespace

import pytest

sys.modules.setdefault("feedparser", SimpleNamespace(parse=lambda *_args, **_kwargs: None))

from app.workers.ingestion import remoteok, remotive, weworkremotely
from app.workers.policy.enforcement import apply_policy_v1


def test_apply_policy_v1_rejects_job():
    job = {
        "job_id": "remoteok:1",
        "title": "Senior PM",
        "description": "100% remote but must be based in the US",
    }

    assert apply_policy_v1(job, source="remoteok") is None


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

    monkeypatch.setattr(module, "init_db", lambda: None)
    monkeypatch.setattr(module, adapter_attr, FakeAdapter)
    monkeypatch.setattr(module, normalize_attr, lambda _: rejected_job)
    monkeypatch.setattr(module, "upsert_job", lambda job: persisted.append(job))

    result = getattr(module, runner_name)()

    assert persisted == []
    assert result["metrics"]["raw_count"] == 1
    assert result["metrics"]["persisted_count"] == 0
    assert result["metrics"]["skipped_count"] == 1
