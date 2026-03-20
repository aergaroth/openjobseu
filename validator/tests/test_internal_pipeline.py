import pytest
from fastapi.testclient import TestClient

import app.api.system as system_api
from app.main import app

client = TestClient(app)


def _is_text_response(response) -> bool:
    return response.headers.get("content-type", "").startswith("text/plain")


def _fake_pipeline_result():
    return {
        "actions": ["pipeline_mocked"],
        "metrics": {
            "tick_duration_ms": 1,
            "ingestion": {
                "source": "employer_ing",
                "raw_count": 1,
                "persisted_count": 1,
                "skipped_count": 0,
            },
        },
    }


@pytest.fixture
def pipeline_spy(monkeypatch):
    calls = []

    def _fake_run_pipeline(*args, **kwargs):
        calls.append({})
        return _fake_pipeline_result()

    monkeypatch.setattr(system_api, "run_pipeline", _fake_run_pipeline)
    return calls


def test_tick_runs_employer_pipeline(monkeypatch, pipeline_spy):
    response = client.post("/internal/tick")

    assert response.status_code == 200
    assert len(pipeline_spy) == 1

    if _is_text_response(response):
        assert "Tick finished (prod)" in response.text
    else:
        data = response.json()
        assert data["mode"] == "prod"
        assert data["sources"] == ["employer_ing"]
        assert "metrics" in data


def test_tick_forces_text_output_with_query_param(monkeypatch, pipeline_spy):
    monkeypatch.setattr(system_api, "should_use_text_logs", lambda: False)

    response = client.post("/internal/tick?format=text")

    assert response.status_code == 200
    assert len(pipeline_spy) == 1
    assert _is_text_response(response)
    assert "Tick finished (prod)" in response.text


def test_tick_forces_json_output_with_query_param(monkeypatch, pipeline_spy):
    monkeypatch.setattr(system_api, "should_use_text_logs", lambda: True)

    response = client.post("/internal/tick?format=json")

    assert response.status_code == 200
    assert len(pipeline_spy) == 1
    assert not _is_text_response(response)
    data = response.json()
    assert data["mode"] == "prod"
    assert data["sources"] == ["employer_ing"]
