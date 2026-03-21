import logging
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security.auth import require_internal_or_user_api_access
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