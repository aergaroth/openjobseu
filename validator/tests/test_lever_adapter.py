import pytest
from unittest.mock import MagicMock
from app.adapters.ats.lever import LeverAdapter


def test_lever_missing_slug_raises_error():
    adapter = LeverAdapter()
    with pytest.raises(ValueError, match="cannot be empty"):
        adapter.fetch({"ats_slug": ""})


def test_lever_fetch_invalid_payload(monkeypatch):
    adapter = LeverAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"error": "not a list"}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    with pytest.raises(ValueError, match="Lever API did not return a list payload"):
        adapter.fetch({"ats_slug": "test-slug"})


def test_lever_fetch_success(monkeypatch):
    adapter = LeverAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = [{"id": "1", "createdAt": 1600000000000}]
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    jobs = adapter.fetch({"ats_slug": "test"})
    assert len(jobs) == 1
    assert jobs[0]["_ats_slug"] == "test"


def test_lever_probe_jobs(monkeypatch):
    adapter = LeverAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"id": "1", "createdAt": 1600000000000, "text": "Remote Dev", "workplaceType": "remote"},
        {"id": "2", "createdAt": 1600000000000, "text": "Local Dev", "workplaceType": "office"}
    ]
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    result = adapter.probe_jobs("test")
    assert result["jobs_total"] == 2
    assert result["remote_hits"] == 1
    assert result["recent_job_at"] is not None


def test_lever_probe_jobs_invalid_payload(monkeypatch):
    adapter = LeverAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"error": "not a list"}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    with pytest.raises(ValueError):
        adapter.probe_jobs("test")
        

def test_lever_probe_jobs_empty_slug():
    adapter = LeverAdapter()
    with pytest.raises(ValueError):
        adapter.probe_jobs("")