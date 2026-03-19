import pytest
from unittest.mock import MagicMock
from app.adapters.ats.workable import WorkableAdapter


def test_workable_fetch_detail_fallback(monkeypatch):
    adapter = WorkableAdapter()
    
    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {
        "results": [
            {"shortcode": "OK123", "title": "Summary Title 1"},
            {"shortcode": "FAIL456", "title": "Summary Title 2"}
        ]
    }
    monkeypatch.setattr(adapter.session, "post", lambda *a, **kw: mock_post_resp)
    
    def mock_get(url, *args, **kwargs):
        if "FAIL456" in url:
            raise RuntimeError("Simulated connection error")
        resp = MagicMock()
        resp.json.return_value = {
            "shortcode": "OK123", 
            "title": "Detail Title 1", 
            "description": "Full Description"
        }
        return resp

    monkeypatch.setattr(adapter.session, "get", mock_get)
    
    jobs = adapter.fetch({"ats_slug": "test-slug"})
    
    # Pierwsza oferta powinna zaktualizować się o widok szczegółowy ("description")
    assert len(jobs) == 2
    assert jobs[0]["title"] == "Detail Title 1"
    assert "description" in jobs[0]
    
    # Druga oferta powinna napotkać błąd (symulowany RuntimeError)
    # lecz mimo to pozostać w wynikach z użyciem fallbacku z głównego zapytania!
    assert jobs[1]["title"] == "Summary Title 2"
    assert "description" not in jobs[1]


def test_workable_probe_jobs_success(monkeypatch):
    adapter = WorkableAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": [
        {"title": "Remote Dev", "location": {"country": "Poland"}, "remote": True, "published": "2023-01-01"},
        "not a dict"
    ]}
    monkeypatch.setattr(adapter.session, "post", lambda *a, **kw: mock_resp)
    
    res = adapter.probe_jobs("test")
    assert res["jobs_total"] == 1
    assert res["remote_hits"] == 1
    assert res["recent_job_at"] is not None

def test_workable_probe_jobs_empty_slug():
    with pytest.raises(ValueError):
        WorkableAdapter().probe_jobs("")

def test_workable_probe_jobs_invalid_payload(monkeypatch):
    adapter = WorkableAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": "not a list"}
    monkeypatch.setattr(adapter.session, "post", lambda *a, **kw: mock_resp)
    with pytest.raises(ValueError):
        adapter.probe_jobs("test")
        
def test_workable_fetch_empty_jobs(monkeypatch):
    adapter = WorkableAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": []}
    monkeypatch.setattr(adapter.session, "post", lambda *a, **kw: mock_resp)
    assert adapter.fetch({"ats_slug": "test"}) == []