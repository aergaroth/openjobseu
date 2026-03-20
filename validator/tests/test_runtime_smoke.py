import pytest
import time
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _is_text_response(response) -> bool:
    return response.headers.get("content-type", "").startswith("text/plain")


def _wait_until_ready(client, timeout_seconds: float = 5.0):
    deadline = time.time() + timeout_seconds
    last_response = None
    while time.time() < deadline:
        last_response = client.get("/ready")
        if last_response.status_code == 200 and last_response.json() == {"ready": True}:
            return
        time.sleep(0.05)

    status_code = last_response.status_code if last_response is not None else "none"
    raise AssertionError(f"/ready did not become ready in time (last_status={status_code})")


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"
    assert "time" in data


def test_ready_endpoint(client):
    _wait_until_ready(client)
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"ready": True}


def test_ready_endpoint_returns_503_when_not_bootstrapped(client):
    _wait_until_ready(client)
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
        "app.api.system.run_pipeline",
        lambda *args, **kwargs: {
            "actions": ["smoke"],
            "metrics": {"tick_duration_ms": 1},
        },
    )
