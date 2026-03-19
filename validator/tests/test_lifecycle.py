import pytest
from app.workers import lifecycle

def test_run_lifecycle_pipeline_execution_order(monkeypatch):
    calls = []

    monkeypatch.setattr(lifecycle, "expire_jobs_due_to_lifecycle", lambda: calls.append("expire"))
    monkeypatch.setattr(lifecycle, "stale_active_jobs_due_to_lifecycle", lambda: calls.append("stale"))
    monkeypatch.setattr(lifecycle, "activate_new_jobs_due_to_lifecycle", lambda: calls.append("activate"))
    monkeypatch.setattr(lifecycle, "reactivate_stale_jobs_due_to_lifecycle", lambda: calls.append("reactivate"))
    monkeypatch.setattr(lifecycle, "mark_reposts_due_to_lifecycle", lambda: calls.append("reposts"))

    lifecycle.run_lifecycle_pipeline()

    # Order matters: expire must run first to remove jobs from other transitions.
    assert calls == [
        "expire",
        "stale",
        "activate",
        "reactivate",
        "reposts"
    ]

def test_run_lifecycle_rules_wrapper_compatibility(monkeypatch):
    calls = []
    monkeypatch.setattr(lifecycle, "run_lifecycle_pipeline", lambda: calls.append("pipeline_called"))
    lifecycle.run_lifecycle_rules()
    assert calls == ["pipeline_called"]