import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _is_text_response(response) -> bool:
    return response.headers.get("content-type", "").startswith("text/plain")


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"
    assert "time" in data


def test_ready_endpoint(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"ready": True}


def test_ready_endpoint_returns_503_when_not_bootstrapped(client):
    previous_ready = getattr(app.state, "ready", False)
    app.state.ready = False
    try:
        resp = client.get("/ready")
    finally:
        app.state.ready = previous_ready

    assert resp.status_code == 503
    assert resp.json() == {"ready": False}


@pytest.fixture(autouse=True)
def _mock_tick(monkeypatch):
    monkeypatch.setattr(
        "app.internal.run_tick_pipeline",
        lambda *args, **kwargs: {
            "actions": ["smoke"],
            "metrics": {"tick_duration_ms": 1},
        },
    )
