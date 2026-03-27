import json
from unittest.mock import patch

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.main import app
import app.api.system as system_api


client = TestClient(app)


def _make_request(path: str = "/internal/tick", headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "scheme": "https",
        "path": path,
        "root_path": "",
        "query_string": b"",
        "headers": headers or [],
        "client": ("198.51.100.10", 44321),
        "server": ("example.test", 443),
    }
    return Request(scope)


def test_system_metrics_endpoint(monkeypatch):
    monkeypatch.setattr(system_api, "get_system_metrics", lambda: {"jobs_total": 100})

    response = client.get("/internal/metrics")

    assert response.status_code == 200
    assert response.json() == {"jobs_total": 100}


@pytest.mark.parametrize(
    ("path", "target", "limit", "updated"),
    [
        ("/internal/backfill-compliance?limit=25", "backfill_missing_compliance_classes", 25, 7),
        ("/internal/backfill-salary?limit=15", "backfill_missing_salary_fields", 15, 5),
    ],
)
def test_backfill_endpoints_forward_limit_and_return_payload(monkeypatch, path, target, limit, updated):
    seen = {}

    def _backfill(*, limit):
        seen["limit"] = limit
        return updated

    monkeypatch.setattr(system_api, target, _backfill)

    response = client.post(path)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "updated_jobs_count": updated}
    assert seen["limit"] == limit


def test_backfill_department_endpoint_returns_response_payload(monkeypatch):
    monkeypatch.setattr(system_api, "backfill_missing_departments", lambda: 3)

    response = client.post("/internal/backfill-department")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "updated_jobs_count": 3}


def test_strip_html_removes_tags_recursively():
    payload = {
        "title": "<b>Hello</b>",
        "nested": [{"value": "<p>World</p>"}, 123, None],
        "plain": "already clean",
    }

    assert system_api._strip_html(payload) == {
        "title": "Hello",
        "nested": [{"value": "World"}, 123, None],
        "plain": "already clean",
    }


def test_preview_job_endpoint(monkeypatch):
    class DummyAdapter:
        def fetch(self, company, updated_since=None):
            return [
                {
                    "id": "123",
                    "title": "Software Engineer",
                    "description": "<p>Test</p>",
                }
            ]

        def normalize(self, raw_job):
            return {
                "source_job_id": "123",
                "title": raw_job["title"],
                "description": "Test",
                "remote_scope": "EU",
            }

    def mock_get_adapter(provider):
        if provider == "greenhouse":
            return DummyAdapter()
        raise ValueError("Unknown ATS provider")

    monkeypatch.setattr(system_api, "get_adapter", mock_get_adapter)
    monkeypatch.setattr(
        system_api,
        "process_ingested_job",
        lambda job, source: (job, {"status": "approved", "compliance_score": 100}),
    )

    response = client.post("/internal/preview-job?provider=greenhouse&slug=test")
    assert response.status_code == 200
    assert "Fetching jobs for 'test' via 'greenhouse'" in response.text
    assert "RAW JOB PAYLOAD" in response.text
    assert "PROCESSED JOB (FINAL)" in response.text

    bad_response = client.post("/internal/preview-job?provider=invalid_ats&slug=test")
    assert bad_response.status_code == 400
    assert "Unknown ATS provider" in bad_response.json()["detail"]


def test_preview_job_endpoint_handles_fetch_errors(monkeypatch):
    class FailingAdapter:
        def fetch(self, company, updated_since=None):
            raise RuntimeError("ATS unavailable")

    monkeypatch.setattr(system_api, "get_adapter", lambda _provider: FailingAdapter())

    response = client.post("/internal/preview-job?provider=greenhouse&slug=test")

    assert response.status_code == 200
    assert "Failed to fetch jobs: ATS unavailable" in response.text


def test_preview_job_endpoint_handles_empty_results(monkeypatch):
    class EmptyAdapter:
        def fetch(self, company, updated_since=None):
            return []

    monkeypatch.setattr(system_api, "get_adapter", lambda _provider: EmptyAdapter())

    response = client.post("/internal/preview-job?provider=greenhouse&slug=test")

    assert response.status_code == 200
    assert "No jobs found for this slug." in response.text


def test_preview_job_endpoint_reports_no_matching_job(monkeypatch):
    class FilteringAdapter:
        def fetch(self, company, updated_since=None):
            return [{"id": "skip-me"}, {"id": "other"}]

        def normalize(self, raw_job):
            if raw_job["id"] == "skip-me":
                return None
            return {
                "source_job_id": raw_job["id"],
                "title": "Backend Engineer",
                "description": "Text",
                "remote_scope": "Europe",
            }

    monkeypatch.setattr(system_api, "get_adapter", lambda _provider: FilteringAdapter())

    response = client.post("/internal/preview-job?provider=greenhouse&slug=test&job_id=missing")

    assert response.status_code == 200
    assert "No matching job found (checked 2 jobs)." in response.text


def test_preview_job_endpoint_handles_rejected_job_and_truncates_raw_payload(monkeypatch):
    class VerboseAdapter:
        def fetch(self, company, updated_since=None):
            return [
                {
                    "id": "123",
                    "description": "<p>" + ("x" * 3500) + "</p>",
                    "nested": {"html": "<b>tagged</b>"},
                }
            ]

        def normalize(self, raw_job):
            return {
                "source_job_id": raw_job["id"],
                "title": "Staff Engineer",
                "description": "long text",
                "remote_scope": "Europe",
            }

    monkeypatch.setattr(system_api, "get_adapter", lambda _provider: VerboseAdapter())
    monkeypatch.setattr(
        system_api,
        "process_ingested_job",
        lambda job, source: (None, {"status": "rejected", "reason": "policy"}),
    )

    response = client.post("/internal/preview-job?provider=greenhouse&slug=test")

    assert response.status_code == 200
    assert "<b>" not in response.text
    assert "... [TRUNCATED]" in response.text
    assert "Job was REJECTED by policy engine and returned None." in response.text


def test_internal_tick_endpoint(monkeypatch):
    monkeypatch.setattr(system_api, "should_use_text_logs", lambda: False)
    pipeline_result = {
        "actions": ["pipeline_mocked"],
        "metrics": {"tick_duration_ms": 1},
    }

    with patch.object(system_api, "run_pipeline", return_value=pipeline_result) as mock_run_pipeline:
        response = client.post("/internal/tick?format=json&group=maintenance")
        assert response.status_code == 200
        assert response.json()["mode"] == "prod"
        mock_run_pipeline.assert_called_once()
        _, kwargs = mock_run_pipeline.call_args
        assert kwargs["group"] == "maintenance"
        assert kwargs["context"]["group"] == "maintenance"
        assert kwargs["context"]["execution_mode"] == "sync_request"
        assert kwargs["context"]["trigger_source"] == "direct_request"


def test_internal_tick_endpoint_error_handling(monkeypatch):
    monkeypatch.setattr(system_api, "should_use_text_logs", lambda: False)
    error_client = TestClient(app, raise_server_exceptions=False)

    with patch.object(system_api, "run_pipeline", side_effect=Exception("Pipeline error")):
        response = error_client.post("/internal/tick?format=json")
        assert response.status_code == 500


def test_internal_tick_endpoint_rejects_invalid_group():
    response = client.post("/internal/tick?group=discovery")
    assert response.status_code == 422


def test_internal_tick_endpoint_format_validation(monkeypatch):
    monkeypatch.setattr(system_api, "should_use_text_logs", lambda: False)
    pipeline_result = {
        "actions": ["pipeline_mocked"],
        "metrics": {"tick_duration_ms": 1},
    }

    with patch.object(system_api, "run_pipeline", return_value=pipeline_result) as mock_run_pipeline:
        response = client.post("/internal/tick?format=text")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        mock_run_pipeline.assert_called_once()
        _, kwargs = mock_run_pipeline.call_args
        assert kwargs["group"] == "all"

    response = client.post("/internal/tick?format=invalid")
    assert response.status_code == 422


def test_tick_dispatches_to_enqueue_when_queue_is_configured(monkeypatch):
    request = _make_request(
        headers=[
            (b"x-cloudscheduler-jobname", b"hourly-sync"),
            (b"x-cloudscheduler-scheduletime", b"2026-03-27T12:00:00Z"),
        ]
    )
    enqueue_calls = []
    monkeypatch.setattr(system_api, "is_tick_queue_configured", lambda: True)
    monkeypatch.setattr(
        system_api,
        "_enqueue_tick",
        lambda **kwargs: enqueue_calls.append(kwargs) or {"status": "accepted"},
    )

    response = system_api.tick(
        request=request,
        response_format="json",
        group="ingestion",
        incremental=False,
        limit=33,
    )

    assert response == {"status": "accepted"}
    assert enqueue_calls[0]["context"]["execution_mode"] == "async_trigger"
    assert enqueue_calls[0]["context"]["trigger_source"] == "cloud_scheduler"
    assert enqueue_calls[0]["context"]["group"] == "ingestion"
    assert enqueue_calls[0]["context"]["incremental"] is False
    assert enqueue_calls[0]["context"]["limit"] == 33


def test_enqueue_tick_returns_json_response_and_passes_cloud_task_payload(monkeypatch):
    request = _make_request()
    seen = {}
    monkeypatch.setenv("BASE_URL", "https://runtime.example")

    def _create_tick_task(**kwargs):
        seen["kwargs"] = kwargs
        return {"name": "task-123"}

    monkeypatch.setattr(system_api, "create_tick_task", _create_tick_task)
    monkeypatch.setattr(system_api, "should_use_text_logs", lambda: False)
    monkeypatch.setattr(system_api, "format_tick_summary", lambda payload: f"summary:{payload['tick_id']}")

    response = system_api._enqueue_tick(
        request=request,
        response_format="json",
        force_text=False,
        context={
            "tick_id": "tick-1",
            "request_id": "req-1",
            "group": "ingestion",
            "incremental": True,
            "limit": 42,
            "scheduler_job_name": "hourly-job",
            "scheduler_schedule_time": "2026-03-27T12:00:00Z",
            "scheduler_execution": "hourly-job@2026-03-27T12:00:00Z",
        },
    )

    assert response.status_code == 202
    assert response.headers["content-type"].startswith("application/json")
    body = json.loads(response.body.decode())
    assert body["status"] == "accepted"
    assert body["task_name"] == "task-123"
    assert seen["kwargs"]["handler_url"] == "https://runtime.example/internal/tick/execute?group=ingestion"
    assert seen["kwargs"]["payload"]["response_format"] == "json"
    assert seen["kwargs"]["headers"]["X-Tick-Id"] == "tick-1"


def test_enqueue_tick_returns_text_response_when_requested(monkeypatch):
    request = _make_request()
    monkeypatch.setattr(system_api, "create_tick_task", lambda **kwargs: {"name": "task-123"})
    monkeypatch.setattr(system_api, "format_tick_summary", lambda payload: f"tick:{payload['tick_id']}")

    response = system_api._enqueue_tick(
        request=request,
        response_format="text",
        force_text=False,
        context={
            "tick_id": "tick-2",
            "request_id": "req-2",
            "group": "maintenance",
            "incremental": True,
            "limit": 10,
        },
    )

    assert response.status_code == 202
    assert response.headers["content-type"].startswith("text/plain")
    assert response.body.decode() == "tick:tick-2"


def test_enqueue_tick_raises_http_500_when_cloud_tasks_fail(monkeypatch):
    request = _make_request()
    monkeypatch.setattr(system_api, "create_tick_task", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(HTTPException) as exc_info:
        system_api._enqueue_tick(
            request=request,
            response_format="json",
            force_text=False,
            context={
                "tick_id": "tick-3",
                "request_id": "req-3",
                "group": "all",
                "incremental": True,
                "limit": 100,
            },
        )

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_execute_tick_merges_headers_and_body_into_context(monkeypatch):
    seen = {}
    request = _make_request(
        path="/internal/tick/execute",
        headers=[
            (b"x-request-id", b"req-header"),
            (b"x-tick-id", b"tick-header"),
            (b"x-scheduler-job-name", b"job-header"),
            (b"x-scheduler-schedule-time", b"2026-03-27T18:00:00Z"),
            (b"x-cloudtasks-taskname", b"task-header"),
        ],
    )

    async def _json():
        return {
            "group": "maintenance",
            "incremental": False,
            "limit": 9,
            "response_format": "text",
            "request_id": "req-body",
            "tick_id": "tick-body",
            "scheduler_job_name": "job-body",
            "scheduler_schedule_time": "2026-03-27T00:00:00Z",
        }

    request.json = _json

    def _build_tick_context(**kwargs):
        seen["context_kwargs"] = kwargs
        return {"tick_id": "tick-header"}

    def _execute_tick(**kwargs):
        seen["execute_kwargs"] = kwargs
        return {"status": "completed"}

    monkeypatch.setattr(
        system_api,
        "build_tick_context",
        _build_tick_context,
    )
    monkeypatch.setattr(system_api, "_execute_tick", _execute_tick)

    response = await system_api.execute_tick(request)

    assert response == {"status": "completed"}
    assert seen["context_kwargs"]["request_id"] == "req-header"
    assert seen["context_kwargs"]["tick_id"] == "tick-header"
    assert seen["context_kwargs"]["group"] == "maintenance"
    assert seen["context_kwargs"]["incremental"] is False
    assert seen["context_kwargs"]["limit"] == 9
    assert seen["context_kwargs"]["execution_mode"] == "async_task"
    assert seen["context_kwargs"]["trigger_source"] == "cloud_tasks"
    assert seen["context_kwargs"]["scheduler_job_name"] == "job-header"
    assert seen["context_kwargs"]["scheduler_schedule_time"] == "2026-03-27T18:00:00Z"
    assert seen["context_kwargs"]["task_name"] == "task-header"
    assert seen["execute_kwargs"]["response_format"] == "text"
    assert seen["execute_kwargs"]["force_text"] is False


def test_execute_tick_sets_worker_globals_and_returns_text(monkeypatch):
    monkeypatch.setattr(system_api, "should_use_text_logs", lambda: True)
    monkeypatch.setattr(system_api, "format_tick_summary", lambda payload: f"summary:{payload['phase']}")
    monkeypatch.setattr(
        system_api,
        "run_pipeline",
        lambda **kwargs: {"actions": ["done"], "metrics": {"group": kwargs["group"]}},
    )

    response = system_api._execute_tick(
        response_format="auto",
        force_text=False,
        context={
            "group": "ingestion",
            "incremental": False,
            "limit": 12,
            "tick_id": "tick-4",
            "request_id": "req-4",
        },
    )

    assert response.headers["content-type"].startswith("text/plain")
    assert response.body.decode() == "summary:pipeline_completed"
    assert system_api.employer_worker.GLOBAL_INCREMENTAL_FETCH is False
    assert system_api.employer_worker.GLOBAL_COMPANIES_LIMIT == 12
