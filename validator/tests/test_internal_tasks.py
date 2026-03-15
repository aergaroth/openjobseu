import logging
import time
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.security.auth import require_internal_or_user_api_access
import app.internal as internal

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_async_tasks():
    """Clear the ASYNC_TASKS registry before each test to ensure isolation."""
    internal.ASYNC_TASKS.clear()
    yield


def test_trigger_invalid_task():
    response = client.post("/internal/tasks/invalid-task-name")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_get_invalid_task_status():
    response = client.get("/internal/tasks/invalid-task-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_task_execution_and_log_capture(monkeypatch):
    def mock_discovery():
        logger = logging.getLogger("openjobseu.discovery")
        logger.info("mocked discovery running")
        return {"mocked": "result"}

    monkeypatch.setattr(internal, "run_discovery_pipeline", mock_discovery)

    post_response = client.post("/internal/tasks/discovery")
    assert post_response.status_code == 200
    post_data = post_response.json()
    assert post_data["task"] == "discovery"
    assert post_data["status"] == "pending"
    task_id = post_data["task_id"]

    # TestClient in FastAPI runs BackgroundTasks sequentially right after
    # responding to the HTTP request. Therefore, the task is already completed here.
    get_response = client.get(f"/internal/tasks/{task_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()

    assert get_data["status"] == "completed"
    assert get_data["result"] == {"mocked": "result"}
    assert "mocked discovery running" in get_data["logs"]
    assert "log_deque" not in get_data
    assert "finished_at" in get_data


def test_task_failure_handling(monkeypatch):
    def mock_failing_task():
        logger = logging.getLogger("openjobseu.guess")
        logger.info("about to fail")
        raise ValueError("simulated error")

    monkeypatch.setattr(internal, "run_ats_guessing", mock_failing_task)

    post_response = client.post("/internal/tasks/guess")
    assert post_response.status_code == 200
    task_id = post_response.json()["task_id"]

    get_response = client.get(f"/internal/tasks/{task_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()

    assert get_data["status"] == "failed"
    assert get_data["error"] == "simulated error"
    assert "about to fail" in get_data["logs"]
    assert "log_deque" not in get_data
    assert "finished_at" in get_data


def test_task_log_truncation(monkeypatch):
    def mock_chatty_task():
        logger = logging.getLogger("openjobseu.chatty")
        for i in range(250):
            logger.info(f"log line {i}")
        return True

    monkeypatch.setattr(internal, "run_careers_discovery", mock_chatty_task)
    task_id = client.post("/internal/tasks/careers").json()["task_id"]
    logs = client.get(f"/internal/tasks/{task_id}").json()["logs"]

    assert "... [TRUNCATED] ..." in logs
    assert "log line 0" not in logs
    assert "log line 50" in logs
    assert "log line 249" in logs
    assert len(logs.split("\n")) == 201  # 200 elements inside deque + 1 element representing the truncation header


def test_cleanup_old_tasks():
    now = time.time()
    
    internal.ASYNC_TASKS["t1"] = {"status": "completed", "finished_at": now - 100}
    internal.ASYNC_TASKS["t2"] = {"status": "completed", "finished_at": now - 700}
    internal.ASYNC_TASKS["t3"] = {"status": "failed", "finished_at": now - 800}
    internal.ASYNC_TASKS["t4"] = {"status": "running"}  # Should not be deleted even if old
    
    internal._cleanup_old_tasks(retention_seconds=600)
    
    assert "t1" in internal.ASYNC_TASKS
    assert "t2" not in internal.ASYNC_TASKS
    assert "t3" not in internal.ASYNC_TASKS
    assert "t4" in internal.ASYNC_TASKS


def test_prevent_concurrent_tasks():
    internal.ASYNC_TASKS["dummy_id"] = {
        "task": "backfill-salary",
        "status": "running"
    }
    
    response = client.post("/internal/tasks/backfill-salary")
    assert response.status_code == 409
    assert response.json()["detail"] == "Task backfill-salary is already running"


def test_tasks_endpoints_are_protected_by_auth():
    def mock_unauthorized():
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[require_internal_or_user_api_access] = mock_unauthorized

    try:
        post_response = client.post("/internal/tasks/discovery")
        assert post_response.status_code == 401
        assert post_response.json()["detail"] == "Not authenticated"

        get_response = client.get("/internal/tasks/dummy-id")
        assert get_response.status_code == 401
        assert get_response.json()["detail"] == "Not authenticated"
    finally:
        app.dependency_overrides.clear()