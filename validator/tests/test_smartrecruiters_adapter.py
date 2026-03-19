import pytest
from unittest.mock import MagicMock
from app.adapters.ats.smartrecruiters import SmartrecruitersAdapter


def test_smartrecruiters_fetch_detail_fallback(monkeypatch):
    adapter = SmartrecruitersAdapter()
    
    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {
        "content": [
            {"id": "OK123", "name": "Summary Title 1"},
            {"id": "FAIL456", "name": "Summary Title 2"}
        ]
    }
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_post_resp)
    
    def mock_get(url, *args, **kwargs):
        if "FAIL456" in url:
            raise RuntimeError("Simulated connection error")
        resp = MagicMock()
        resp.json.return_value = {
            "jobAd": {
                "sections": {
                    "jobDescription": {"text": "Full Description"}
                }
            }
        }
        return resp

    # Hack the get to return lists on first call, details on later calls
    original_get = adapter.session.get
    monkeypatch.setattr(adapter.session, "get", lambda url, *a, **kw: mock_post_resp if "?limit" in url else mock_get(url))
    
    jobs = adapter.fetch({"ats_slug": "test-slug"})
    
    assert len(jobs) == 2
    assert "Full Description" in jobs[0].get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", "")
    
    assert jobs[1]["name"] == "Summary Title 2"
    assert "jobAd" not in jobs[1]