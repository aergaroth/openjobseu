import os
from fastapi.testclient import TestClient
from app.workers.ingestion.registry import get_available_ingestion_sources

from app.main import app

client = TestClient(app)


def _is_text_response(response) -> bool:
    return response.headers.get("content-type", "").startswith("text/plain")


def test_tick_runs_all_adapters_by_default(monkeypatch):

    monkeypatch.setenv("INGESTION_MODE", "prod")

    # source of truth for available adapters lives in app.internal
    monkeypatch.setenv(
        "INGESTION_SOURCES",
        ",".join(get_available_ingestion_sources()),
    )

    response = client.post("/internal/tick")
    assert response.status_code == 200

    if _is_text_response(response):
        body = response.text
        assert "Tick finished (prod)" in body
        for source in get_available_ingestion_sources():
            assert source in body
    else:
        data = response.json()
        sources = data["sources"]

        assert set(sources) == set(get_available_ingestion_sources())
        assert "metrics" in data



def test_tick_runs_only_selected_adapter(monkeypatch):
    monkeypatch.setenv("INGESTION_MODE", "prod")
    monkeypatch.setenv("INGESTION_SOURCES", "remotive")

    response = client.post("/internal/tick")

    assert response.status_code == 200

    if _is_text_response(response):
        body = response.text
        assert "Tick finished (prod)" in body
        assert "remotive" in body
    else:
        data = response.json()
        assert data["sources"] == ["remotive"]
        assert "metrics" in data


def test_tick_local_mode(monkeypatch):
    monkeypatch.setenv("INGESTION_MODE", "local")
    monkeypatch.delenv("INGESTION_SOURCES", raising=False)

    response = client.post("/internal/tick")

    assert response.status_code == 200

    if _is_text_response(response):
        body = response.text
        assert "Tick finished (local)" in body
        assert "local" in body
    else:
        data = response.json()
        assert data["mode"] == "local"
        assert data["sources"] == ["local"] or "local_ingested" in " ".join(data["actions"])
        assert "metrics" in data


def test_tick_ignores_unknown_source(monkeypatch):
    monkeypatch.setenv("INGESTION_MODE", "prod")
    monkeypatch.setenv("INGESTION_SOURCES", "weworkremotely,unknown")

    response = client.post("/internal/tick")

    assert response.status_code == 200

    if _is_text_response(response):
        body = response.text
        assert "Tick finished (prod)" in body
        assert "weworkremotely" in body
    else:
        data = response.json()
        assert "weworkremotely" in data["sources"]
        assert "metrics" in data
