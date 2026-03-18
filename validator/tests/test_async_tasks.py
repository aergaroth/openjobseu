import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.internal as internal_api

client = TestClient(app)

def test_cancel_async_task_running(monkeypatch):
    """Testuje czy żądanie anulowania poprawnie ustawia flagę cancel_requested dla trwającego zadania."""
    task_id = "test-task-123"
    mock_tasks = {
        task_id: {"status": "running", "task": "backfill-salary"}
    }
    monkeypatch.setattr(internal_api, "ASYNC_TASKS", mock_tasks)

    response = client.post(f"/internal/tasks/{task_id}/cancel")
    
    assert response.status_code == 200
    assert response.json() == {"status": "cancel_requested"}
    assert mock_tasks[task_id].get("cancel_requested") is True

def test_cancel_async_task_already_completed(monkeypatch):
    """Testuje czy próba anulowania zakończonego zadania jest ignorowana i zwraca jego status."""
    task_id = "test-task-456"
    mock_tasks = {
        task_id: {"status": "completed", "task": "tick"}
    }
    monkeypatch.setattr(internal_api, "ASYNC_TASKS", mock_tasks)

    response = client.post(f"/internal/tasks/{task_id}/cancel")
    
    assert response.status_code == 200
    assert response.json() == {"status": "completed"}
    assert "cancel_requested" not in mock_tasks[task_id]

def test_cancel_async_task_not_found(monkeypatch):
    """Testuje błąd 404 dla nieistniejącego ID zadania."""
    monkeypatch.setattr(internal_api, "ASYNC_TASKS", {})
    response = client.post("/internal/tasks/non-existent-id/cancel")
    assert response.status_code == 404

def test_run_backfill_salary_task_respects_cancel_flag(monkeypatch):
    """Testuje czy główna pętla zadania backfill przerywa pracę gdy pojawi się flaga cancel."""
    task_id = "test-cancel-loop-123"
    internal_api.ASYNC_TASKS[task_id] = {
        "status": "running",
        "task": "backfill-salary"
    }

    call_state = {"chunks_processed": 0}

    def mock_backfill(limit):
        call_state["chunks_processed"] += 1
        if call_state["chunks_processed"] == 1:
            # Symulujemy kliknięcie anulowania przez użytkownika w trakcie trwania pierwszej paczki
            internal_api.ASYNC_TASKS[task_id]["cancel_requested"] = True
            return 5 # Przetworzono 5 ofert
        return 10 # Ta część kodu nigdy nie powinna zostać osiągnięta

    monkeypatch.setattr(internal_api, "backfill_missing_salary_fields", mock_backfill)

    result = internal_api.run_backfill_salary_task(limit=100, task_id=task_id)

    assert result == {"status": "cancelled", "updated_jobs_count": 5}
    assert call_state["chunks_processed"] == 1 # Funkcja powinna wywołać backfill tylko raz i zrzucić pętlę