from fastapi.testclient import TestClient

from app.main import app
import app.api.tasks as tasks_api

client = TestClient(app)


def test_tasks_execute_endpoint_processes_payload(monkeypatch):
    """Weryfikuje czy endpoint wykonujący zadanie dla Cloud Tasks odpowiednio deleguje parametry z body."""

    def mock_backfill(limit):
        return {"processed": 100, "updated": 100}

    monkeypatch.setattr(tasks_api, "backfill_missing_salary_fields", mock_backfill)

    response = client.post(
        "/internal/tasks/backfill-salary/execute",
        json={"limit": 100, "incremental": False},
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "result": {"status": "completed", "processed_jobs_count": 100, "updated_jobs_count": 100},
    }
