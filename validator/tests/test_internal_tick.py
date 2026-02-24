import pytest
from fastapi.testclient import TestClient

import app.internal as internal
from app.main import app
from app.workers.ingestion.registry import get_available_ingestion_sources

client = TestClient(app)


def _is_text_response(response) -> bool:
    return response.headers.get("content-type", "").startswith("text/plain")


def _fake_pipeline_result():
    return {
        "actions": ["pipeline_mocked"],
        "metrics": {
            "tick_duration_ms": 1,
            "ingestion": {
                "raw_count": 1,
                "persisted_count": 1,
                "skipped_count": 0,
                "per_source": {},
            },
        },
    }


def _fake_local_result():
    return {
        "actions": ["local_ingested:1"],
        "metrics": {
            "tick_duration_ms": 1,
            "ingestion": {
                "raw_count": 1,
                "persisted_count": 1,
                "skipped_count": 0,
                "per_source": {},
            },
        },
    }


@pytest.fixture
def pipeline_spy(monkeypatch):
    calls = []

    def _fake_run_tick_pipeline(*, ingestion_sources, ingestion_handlers):
        calls.append(
            {
                "ingestion_sources": list(ingestion_sources),
                "ingestion_handlers": ingestion_handlers,
            }
        )
        return _fake_pipeline_result()

    monkeypatch.setattr(internal, "run_tick_pipeline", _fake_run_tick_pipeline)
    return calls


@pytest.fixture
def local_spy(monkeypatch):
    calls = []

    def _fake_run_tick():
        calls.append({})
        return _fake_local_result()

    monkeypatch.setattr(internal, "run_tick", _fake_run_tick)
    return calls


def test_tick_runs_all_adapters_by_default(monkeypatch, pipeline_spy, local_spy):
    monkeypatch.setenv("INGESTION_MODE", "prod")
    expected_sources = get_available_ingestion_sources()
    monkeypatch.setenv("INGESTION_SOURCES", ",".join(expected_sources))

    response = client.post("/internal/tick")

    assert response.status_code == 200
    assert len(pipeline_spy) == 1
    assert pipeline_spy[0]["ingestion_sources"] == expected_sources
    assert pipeline_spy[0]["ingestion_handlers"] is internal.INGESTION_HANDLERS
    assert len(local_spy) == 0

    if _is_text_response(response):
        assert "Tick finished (prod)" in response.text
    else:
        data = response.json()
        assert set(data["sources"]) == set(expected_sources)
        assert "metrics" in data


def test_tick_runs_only_selected_adapter(monkeypatch, pipeline_spy, local_spy):
    monkeypatch.setenv("INGESTION_MODE", "prod")
    monkeypatch.setenv("INGESTION_SOURCES", "remotive")

    response = client.post("/internal/tick")

    assert response.status_code == 200
    assert len(pipeline_spy) == 1
    assert pipeline_spy[0]["ingestion_sources"] == ["remotive"]
    assert pipeline_spy[0]["ingestion_handlers"] is internal.INGESTION_HANDLERS
    assert len(local_spy) == 0

    if _is_text_response(response):
        assert "Tick finished (prod)" in response.text
    else:
        data = response.json()
        assert data["sources"] == ["remotive"]
        assert "metrics" in data


def test_tick_local_mode(monkeypatch, pipeline_spy, local_spy):
    monkeypatch.setenv("INGESTION_MODE", "local")
    monkeypatch.delenv("INGESTION_SOURCES", raising=False)

    response = client.post("/internal/tick")

    assert response.status_code == 200
    assert len(local_spy) == 1
    assert len(pipeline_spy) == 0

    if _is_text_response(response):
        assert "Tick finished (local)" in response.text
    else:
        data = response.json()
        assert data["mode"] == "local"
        assert data["sources"] == ["local"]
        assert "metrics" in data


def test_tick_passes_unknown_source_to_pipeline(monkeypatch, pipeline_spy, local_spy):
    monkeypatch.setenv("INGESTION_MODE", "prod")
    monkeypatch.setenv("INGESTION_SOURCES", "weworkremotely,unknown")

    response = client.post("/internal/tick")

    assert response.status_code == 200
    assert len(pipeline_spy) == 1
    assert pipeline_spy[0]["ingestion_sources"] == ["weworkremotely", "unknown"]
    assert pipeline_spy[0]["ingestion_handlers"] is internal.INGESTION_HANDLERS
    assert len(local_spy) == 0

    if _is_text_response(response):
        assert "Tick finished (prod)" in response.text
    else:
        data = response.json()
        assert data["sources"] == ["weworkremotely", "unknown"]
        assert "metrics" in data
