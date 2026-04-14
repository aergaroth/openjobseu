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
