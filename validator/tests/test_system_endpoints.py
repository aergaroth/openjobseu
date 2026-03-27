from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
import app.api.system as system_api


client = TestClient(app)


def test_system_metrics_endpoint(monkeypatch):
    monkeypatch.setattr(system_api, "get_system_metrics", lambda: {"jobs_total": 100})
    response = client.get("/internal/metrics")
    assert response.status_code == 200
    assert response.json() == {"jobs_total": 100}


def test_preview_job_endpoint(monkeypatch):
    class DummyAdapter:
        def fetch(self, company, updated_since=None):
            return [
                {
                    "id": "123",
                    "title": "Software Engineer",
                    "description": "<p>Test</p>",
                }
            ]

        def normalize(self, raw_job):
            return {
                "source_job_id": "123",
                "title": raw_job["title"],
                "description": "Test",
                "remote_scope": "EU",
            }

    def mock_get_adapter(provider):
        if provider == "greenhouse":
            return DummyAdapter()
        raise ValueError("Unknown ATS provider")

    monkeypatch.setattr(system_api, "get_adapter", mock_get_adapter)
    monkeypatch.setattr(
        system_api,
        "process_ingested_job",
        lambda job, source: (job, {"status": "approved", "compliance_score": 100}),
    )

    response = client.post("/internal/preview-job?provider=greenhouse&slug=test")
    assert response.status_code == 200
    assert "Fetching jobs for 'test' via 'greenhouse'" in response.text
    assert "RAW JOB PAYLOAD" in response.text
    assert "PROCESSED JOB (FINAL)" in response.text

    bad_response = client.post("/internal/preview-job?provider=invalid_ats&slug=test")
    assert bad_response.status_code == 400
    assert "Unknown ATS provider" in bad_response.json()["detail"]


def test_internal_tick_endpoint(monkeypatch):
    """Test endpoint /internal/tick z różnymi parametrami."""
    monkeypatch.setattr(system_api, "should_use_text_logs", lambda: False)
    pipeline_result = {
        "actions": ["pipeline_mocked"],
        "metrics": {"tick_duration_ms": 1},
    }

    with patch.object(system_api, "run_pipeline", return_value=pipeline_result) as mock_run_pipeline:
        response = client.post("/internal/tick?format=json&group=maintenance")
        assert response.status_code == 200
        assert response.json()["mode"] == "prod"
        mock_run_pipeline.assert_called_once()
        _, kwargs = mock_run_pipeline.call_args
        assert kwargs["group"] == "maintenance"
        assert kwargs["context"]["group"] == "maintenance"
        assert kwargs["context"]["execution_mode"] == "sync_request"
        assert kwargs["context"]["trigger_source"] == "direct_request"


def test_internal_tick_endpoint_error_handling(monkeypatch):
    """Test obsługi błędów w endpointcie /internal/tick."""
    monkeypatch.setattr(system_api, "should_use_text_logs", lambda: False)
    error_client = TestClient(app, raise_server_exceptions=False)

    with patch.object(system_api, "run_pipeline", side_effect=Exception("Pipeline error")):
        response = error_client.post("/internal/tick?format=json")
        assert response.status_code == 500


def test_internal_tick_endpoint_rejects_invalid_group():
    """Test walidacji parametru group."""
    response = client.post("/internal/tick?group=discovery")
    assert response.status_code == 422


def test_internal_tick_endpoint_format_validation(monkeypatch):
    """Test walidacji parametru format."""
    monkeypatch.setattr(system_api, "should_use_text_logs", lambda: False)
    pipeline_result = {
        "actions": ["pipeline_mocked"],
        "metrics": {"tick_duration_ms": 1},
    }

    with patch.object(system_api, "run_pipeline", return_value=pipeline_result) as mock_run_pipeline:
        response = client.post("/internal/tick?format=text")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        mock_run_pipeline.assert_called_once()
        _, kwargs = mock_run_pipeline.call_args
        assert kwargs["group"] == "all"

    response = client.post("/internal/tick?format=invalid")
    assert response.status_code == 422
