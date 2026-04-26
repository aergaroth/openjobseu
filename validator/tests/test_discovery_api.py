from fastapi.testclient import TestClient

from app.main import app
import app.api.discovery as discovery_api

client = TestClient(app)


def test_discovery_slug_candidates_endpoint(monkeypatch):
    fake_rows = [
        {
            "id": 1,
            "provider": "teamtailor",
            "slug": "career",
            "discovery_source": "slug_harvest",
            "status": "needs_token",
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]

    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class DummyEngine:
        def connect(self):
            return DummyConn()

    monkeypatch.setattr(discovery_api, "get_engine", lambda: DummyEngine())
    monkeypatch.setattr(discovery_api, "get_discovered_slugs", lambda conn, **kwargs: fake_rows)

    response = client.get("/internal/discovery/slug-candidates")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["provider"] == "teamtailor"
    assert payload["results"][0]["status"] == "needs_token"


def test_discovery_slug_harvest_ops_endpoint(monkeypatch):
    monkeypatch.setattr(
        discovery_api,
        "run_slug_harvest",
        lambda: {"companies_scanned": 5, "candidates_saved": 2},
    )

    response = client.post("/internal/discovery/slug-harvest")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pipeline"] == "discovery"
    assert payload["phase"] == "slug_harvest"
    assert payload["metrics"]["companies_scanned"] == 5
    assert payload["metrics"]["candidates_saved"] == 2


def test_discovery_promote_discovered_ops_endpoint(monkeypatch):
    monkeypatch.setattr(
        discovery_api,
        "run_promote_discovered_slugs",
        lambda: {"slugs_processed": 10, "slugs_promoted": 3, "slugs_rejected": 7},
    )

    response = client.post("/internal/discovery/promote-discovered")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pipeline"] == "discovery"
    assert payload["phase"] == "promote_discovered"
    assert payload["metrics"]["slugs_processed"] == 10
    assert payload["metrics"]["slugs_promoted"] == 3
