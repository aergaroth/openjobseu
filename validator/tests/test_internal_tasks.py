import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.api.tasks as tasks_api

client = TestClient(app)


def test_trigger_invalid_task():
    response = client.post("/internal/tasks/invalid-task-name")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_task_execution_local_fallback(monkeypatch):
    """
    Skoro w środowisku testowym brakuje zmiennych konfiguracyjnych dla Cloud Tasks,
    endpoint powinnien obsłużyć żądanie synchronicznie jako fallback.
    """

    def mock_discovery():
        return {"mocked": "result"}

    # Podmieniamy referencję do funkcji bezpośrednio w słowniku inicjowanym przy starcie modułu
    monkeypatch.setitem(tasks_api.TASK_MAP, "discovery", mock_discovery)

    post_response = client.post("/internal/tasks/discovery")
    assert post_response.status_code == 200
    post_data = post_response.json()

    assert post_data["task"] == "discovery"
    assert post_data["status"] == "completed"
    assert "task_id" in post_data
    assert post_data["result"] == {"mocked": "result"}


def test_cloud_tasks_enqueuing_behavior(monkeypatch):
    monkeypatch.setattr(tasks_api, "is_tick_queue_configured", lambda: True)

    def mock_create_tick_task(task_id, handler_url, payload, headers):
        assert handler_url.endswith("/internal/tasks/discovery/execute")
        assert payload["incremental"] is True
        return {"name": "projects/xyz/locations/xyz/queues/xyz/tasks/xyz"}

    monkeypatch.setattr(tasks_api, "create_tick_task", mock_create_tick_task)

    response = client.post("/internal/tasks/discovery?incremental=true")
    assert response.status_code == 202

    data = response.json()
    assert data["status"] == "enqueued"
    assert data["cloud_task_name"] is not None


@pytest.mark.parametrize(
    ("task_name", "path"),
    [
        ("company-sources", "/internal/tasks/company-sources"),
        ("careers", "/internal/tasks/careers"),
        ("ats-reverse", "/internal/tasks/ats-reverse"),
        ("guess", "/internal/tasks/guess"),
        ("slug-harvest", "/internal/tasks/slug-harvest"),
        ("promote-discovered", "/internal/tasks/promote-discovered"),
    ],
)
def test_discovery_task_endpoints_enqueue_expected_handlers(monkeypatch, task_name, path):
    monkeypatch.setattr(tasks_api, "is_tick_queue_configured", lambda: True)

    def mock_create_tick_task(task_id, handler_url, payload, headers):
        assert task_id
        assert handler_url.endswith(f"/internal/tasks/{task_name}/execute")
        assert payload == {"incremental": True, "limit": 100}
        assert headers == {"Content-Type": "application/json"}
        return {"name": f"projects/xyz/locations/xyz/queues/xyz/tasks/{task_name}"}

    monkeypatch.setattr(tasks_api, "create_tick_task", mock_create_tick_task)

    response = client.post(path)
    assert response.status_code == 202

    data = response.json()
    assert data["task"] == task_name
    assert data["status"] == "enqueued"
    assert data["cloud_task_name"].endswith(task_name)


def test_task_map_includes_split_discovery_phases():
    assert {
        "company-sources",
        "careers",
        "ats-reverse",
        "guess",
        "slug-harvest",
        "promote-discovered",
    }.issubset(tasks_api.TASK_MAP)


def test_cloud_tasks_enqueuing_error_handling(monkeypatch):
    """
    Testuje zachowanie API w przypadku niedostępności lub awarii usługi Google Cloud Tasks.
    """
    monkeypatch.setattr(tasks_api, "is_tick_queue_configured", lambda: True)

    def mock_create_tick_task_fail(*args, **kwargs):
        # Symulujemy błąd zgłoszony przez bibliotekę requests (np. timeout lub 503 z GCP)
        raise RuntimeError("GCP API Connection Timeout")

    monkeypatch.setattr(tasks_api, "create_tick_task", mock_create_tick_task_fail)

    response = client.post("/internal/tasks/discovery?incremental=true")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to enqueue task in Cloud Tasks"
