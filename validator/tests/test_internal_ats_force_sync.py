import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_force_sync_ats_success(monkeypatch):
    # Mock database record
    def mock_get_ats(*args, **kwargs):
        return {
            "ats_provider": "ashby",
            "ats_slug": "test-slug",
            "company_id": "test-id",
            "legal_name": "Test Co",
        }
    monkeypatch.setattr("app.internal.get_ats_integration_by_id", mock_get_ats)

    # Mock adapter implementation
    class DummyAdapter:
        def fetch(self, company, updated_since=None):
            # Simulate finding 3 jobs
            return [{"id": "1"}, {"id": "2"}, {"id": "3"}]

    monkeypatch.setattr("app.internal.ADAPTER_MAP", {"ashby": DummyAdapter})

    # Request (Auth is bypassed automatically because testclient is whitelisted)
    response = client.post("/internal/audit/ats-force-sync/fake_id")
    
    assert response.status_code == 200
    assert "Force sync successful" in response.text
    assert "Fetched 3 jobs" in response.text


def test_api_force_sync_ats_not_found(monkeypatch):
    monkeypatch.setattr("app.internal.get_ats_integration_by_id", lambda *args, **kwargs: None)

    response = client.post("/internal/audit/ats-force-sync/unknown_id")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "ATS integration not found"


def test_api_force_sync_unauthorized_external_request():
    # Standard request (not TestClient) should be blocked without a session
    response = client.post("/internal/audit/ats-force-sync/123", headers={"host": "external.com"})
    assert response.status_code in (401, 403)