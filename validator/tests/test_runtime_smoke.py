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


def test_internal_tick_smoke():
    resp = client.post("/internal/tick")
    assert resp.status_code == 200

    if _is_text_response(resp):
        body = resp.text
        assert "Tick finished" in body
        assert "TOTALS" in body
    else:
        data = resp.json()
        assert data["status"] == "ok"
        assert "actions" in data
        assert "metrics" in data
        assert "tick_duration_ms" in data["metrics"]
