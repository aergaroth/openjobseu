import pytest
from fastapi.testclient import TestClient

import app.api.system as system_api
from app.main import app

client = TestClient(app)


def test_system_metrics_endpoint(monkeypatch):
    monkeypatch.setattr(system_api, "get_system_metrics", lambda: {"jobs_total": 100})
    response = client.get("/internal/metrics")
    assert response.status_code == 200
    assert response.json() == {"jobs_total": 100}


def test_preview_job_endpoint(monkeypatch):
    class DummyAdapter:
        def fetch(self, company, updated_since=None):
            return [{"id": "123", "title": "Software Engineer", "description": "<p>Test</p>"}]
        def normalize(self, raw_job):
            return {"source_job_id": "123", "title": raw_job["title"], "description": "Test", "remote_scope": "EU"}
            
    def mock_get_adapter(provider):
        if provider == "greenhouse":
            return DummyAdapter()
        raise ValueError("Unknown ATS provider")

    monkeypatch.setattr(system_api, "get_adapter", mock_get_adapter)
    monkeypatch.setattr(
        system_api, 
        "process_ingested_job", 
        lambda job, source: (job, {"status": "approved", "compliance_score": 100})
    )

    response = client.post("/internal/preview-job?provider=greenhouse&slug=test")
    assert response.status_code == 200
    assert "Fetching jobs for 'test' via 'greenhouse'" in response.text
    assert "RAW JOB PAYLOAD" in response.text
    assert "PROCESSED JOB (FINAL)" in response.text
    
    bad_response = client.post("/internal/preview-job?provider=invalid_ats&slug=test")
    assert bad_response.status_code == 400
    assert "Unknown ATS provider" in bad_response.json()["detail"]