import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def _is_text_response(response) -> bool:
    return response.headers.get("content-type", "").startswith("text/plain")


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"
    assert "time" in data


def test_ready_endpoint():
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"ready": True}



@pytest.fixture(autouse=True)
def _mock_tick(monkeypatch):
    monkeypatch.setattr(
        "app.internal.run_tick_pipeline",
        lambda *args, **kwargs: {
            "actions": ["smoke"],
            "metrics": {"tick_duration_ms": 1},
        },
    )
    monkeypatch.setattr(
        "app.internal.run_tick",
        lambda *args, **kwargs: {
            "actions": ["local_smoke"],
            "metrics": {"tick_duration_ms": 1},
        },
    )

