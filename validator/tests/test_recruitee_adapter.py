import pytest
from unittest.mock import MagicMock
from app.adapters.ats.recruitee import RecruiteeAdapter


def test_recruitee_fetch_invalid_payload(monkeypatch):
    adapter = RecruiteeAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"offers": "not a list"}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    with pytest.raises(ValueError, match="did not return an offers list"):
        adapter.fetch({"ats_slug": "test-slug"})
        
        
def test_recruitee_fetch_null_offers(monkeypatch):
    adapter = RecruiteeAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"offers": None}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    assert adapter.fetch({"ats_slug": "test-slug"}) == []

def test_recruitee_fetch_success(monkeypatch):
    adapter = RecruiteeAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"offers": [{"id": 1, "created_at": "2023-01-01T00:00:00Z"}]}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    jobs = adapter.fetch({"ats_slug": "test"})
    assert len(jobs) == 1
    assert jobs[0]["_ats_slug"] == "test"

def test_recruitee_probe_jobs(monkeypatch):
    adapter = RecruiteeAdapter()
    monkeypatch.setattr(adapter, "fetch", lambda company, **kw: [
        {"title": "Dev", "location": "Remote", "remote": True, "created_at": "2023-01-01T00:00:00Z"}
    ])
    res = adapter.probe_jobs("test")
    assert res["jobs_total"] == 1
    assert res["remote_hits"] == 1
    assert res["recent_job_at"] == "2023-01-01T00:00:00Z"

def test_recruitee_probe_jobs_empty(monkeypatch):
    adapter = RecruiteeAdapter()
    monkeypatch.setattr(adapter, "fetch", lambda company, **kw: [])
    assert adapter.probe_jobs("test") is None


def test_recruitee_fetch_missing_slug():
    adapter = RecruiteeAdapter()
    assert adapter.fetch({"ats_slug": ""}) == []
    assert adapter.fetch({}) == []


def test_recruitee_normalize_missing_slug_and_id():
    adapter = RecruiteeAdapter()
    assert adapter.normalize({"id": 123, "title": "Dev"}) is None
    assert adapter.normalize({"_ats_slug": "test", "title": "Dev"}) is None


def test_recruitee_normalize_success():
    adapter = RecruiteeAdapter()
    raw_job = {
        "_ats_slug": "test-co",
        "id": 123,
        "title": "Backend Dev",
        "location": "Remote",
        "careers_url": "https://test.recruitee.com/o/123",
        "department": "Engineering",
        "remote": True,
        "description": "Desc",
        "requirements": "Reqs",
        "company_name": "Test Co Explicit"
    }
    job = adapter.normalize(raw_job)
    assert job["job_id"] == "recruitee:test-co:123"
    assert job["company_name"] == "Test Co Explicit"
    assert job["remote_source_flag"] is True
    assert "Desc" in job["description"]
    assert "Reqs" in job["description"]

def test_recruitee_normalize_fallback_company_name():
    adapter = RecruiteeAdapter()
    assert adapter.normalize({"_ats_slug": "acme-inc", "id": 456})["company_name"] == "Acme Inc"