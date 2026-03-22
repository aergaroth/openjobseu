import pytest
from unittest.mock import MagicMock
from app.adapters.ats.ashby import AshbyAdapter


def test_ashby_probe_invalid_payload(monkeypatch):
    adapter = AshbyAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"jobs": "not a list"}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    with pytest.raises(ValueError, match="did not return a jobs list"):
        adapter.probe_jobs("test-slug")


def test_ashby_missing_slug_and_invalid_normalize():
    adapter = AshbyAdapter()

    with pytest.raises(ValueError, match="cannot be empty"):
        adapter.fetch({"ats_slug": ""})

    # Oferta pozbawiona ID musi zostać w całości zignorowana, zwracając None
    assert adapter.normalize({"_ats_slug": "ok", "title": "Dev", "jobUrl": "url"}) is None


def test_ashby_fetch_success(monkeypatch):
    adapter = AshbyAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"jobs": [{"id": "1", "updatedAt": "2023-01-01T00:00:00Z"}]}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    jobs = adapter.fetch({"ats_slug": "test"})
    assert len(jobs) == 1
    assert jobs[0]["_ats_slug"] == "test"


def test_ashby_probe_jobs_success(monkeypatch):
    adapter = AshbyAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "jobs": [
            {
                "title": "Dev",
                "location": "Remote",
                "isRemote": True,
                "updatedAt": "2023-01-01T00:00:00Z",
            },
            "not a dict",
        ]
    }
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    res = adapter.probe_jobs("test")
    assert res["jobs_total"] == 1
    assert res["remote_hits"] == 1
    assert res["recent_job_at"] is not None


def test_ashby_probe_jobs_empty_slug():
    with pytest.raises(ValueError):
        AshbyAdapter().probe_jobs("")
