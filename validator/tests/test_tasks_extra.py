from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.api.tasks import run_backfill_compliance_task, run_backfill_salary_task, run_tick_task
import app.workers.ingestion.employer as employer_worker

client = TestClient(app)


@patch("app.api.tasks.backfill_missing_compliance_classes")
def test_run_backfill_compliance_task(mock_backfill):
    # Symulujemy, że po 1.5 paczki brakło już danych do aktualizacji w bazie
    mock_backfill.side_effect = [1000, 500, 0]
    res = run_backfill_compliance_task(limit=2000)
    assert res["updated_jobs_count"] == 1500


@patch("app.api.tasks.backfill_missing_salary_fields")
def test_run_backfill_salary_task(mock_backfill):
    mock_backfill.side_effect = [1000, 0]
    res = run_backfill_salary_task(limit=1500)
    assert res["updated_jobs_count"] == 1000


@patch("app.api.tasks.run_pipeline")
def test_run_tick_task(mock_run_pipeline):
    mock_run_pipeline.return_value = {"status": "ok"}
    res = run_tick_task(incremental=False, limit=42)

    assert res == {"status": "ok"}
    assert employer_worker.GLOBAL_INCREMENTAL_FETCH is False
    assert employer_worker.GLOBAL_COMPANIES_LIMIT == 42


def test_execute_task_exception(monkeypatch):
    import app.api.tasks as tasks_api

    def mock_failing_task():
        raise ValueError("Something went wrong")

    monkeypatch.setitem(tasks_api.TASK_MAP, "discovery", mock_failing_task)

    res = client.post("/internal/tasks/discovery/execute", json={})
    assert res.status_code == 500
    assert res.json()["detail"] == "Something went wrong"


def test_execute_task_backfill(monkeypatch):
    res = client.post("/internal/tasks/backfill-compliance/execute", json={"limit": 50})
    assert res.status_code == 200
