import os
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_tick_runs_all_adapters_by_default(monkeypatch):
    monkeypatch.delenv("INGESTION_SOURCES", raising=False)
    monkeypatch.setenv("INGESTION_MODE", "prod")

    response = client.post("/internal/tick")

    assert response.status_code == 200

    data = response.json()
    sources = data["sources"]

    # kolejność nieistotna
    assert set(sources) == {"rss", "remotive"}


def test_tick_runs_only_selected_adapter(monkeypatch):
    monkeypatch.setenv("INGESTION_MODE", "prod")
    monkeypatch.setenv("INGESTION_SOURCES", "rss")

    response = client.post("/internal/tick")

    assert response.status_code == 200

    data = response.json()
    assert data["sources"] == ["rss"]


def test_tick_local_mode(monkeypatch):
    monkeypatch.setenv("INGESTION_MODE", "local")
    monkeypatch.delenv("INGESTION_SOURCES", raising=False)

    response = client.post("/internal/tick")

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "local"
    assert data["sources"] == ["local"] or "local_ingested" in " ".join(data["actions"])


def test_tick_ignores_unknown_source(monkeypatch):
    monkeypatch.setenv("INGESTION_MODE", "prod")
    monkeypatch.setenv("INGESTION_SOURCES", "rss,unknown")

    response = client.post("/internal/tick")

    assert response.status_code == 200

    data = response.json()
    assert "rss" in data["sources"]

