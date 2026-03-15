import pytest
from app.workers.discovery import pipeline
from app.workers.discovery import ats_reverse


def test_run_discovery_pipeline_handles_step_error(monkeypatch):
    calls = []

    def step_1_success():
        calls.append("step_1")
        return {"processed": 10}

    def step_2_fails():
        calls.append("step_2")
        raise RuntimeError("network timeout")

    def step_3_success():
        calls.append("step_3")
        return {"processed": 5}

    fake_steps = [
        ("step_one", step_1_success),
        ("step_two", step_2_fails),
        ("step_three", step_3_success),
    ]

    monkeypatch.setattr(pipeline, "PIPELINE_STEPS", fake_steps)

    result = pipeline.run_discovery_pipeline()

    # Ensure all steps were called in the correct order (the error did not break the loop)
    assert calls == ["step_1", "step_2", "step_3"]

    metrics = result["metrics"]
    assert metrics["status"] == "error"  # Overall status was marked as error
    assert metrics["step_one"] == {"processed": 10}
    assert metrics["step_two"]["status"] == "error"
    assert "network timeout" in metrics["step_two"]["error"]
    assert metrics["step_three"] == {"processed": 5}
    assert "duration_ms" in metrics


def test_ats_reverse_handles_db_errors(monkeypatch):
    monkeypatch.setattr(ats_reverse, "PROVIDERS_TO_PROBE", ["test_provider"])
    monkeypatch.setattr(ats_reverse, "_load_slugs", lambda: ["ok1", "fail1", "ok2"])

    monkeypatch.setattr(
        ats_reverse,
        "probe_ats",
        lambda p, s: {"jobs_total": 5, "remote_hits": 2, "recent_job_at": None}
    )

    # Dummy DB Context
    class DummyConn: pass
    class DummyCtx:
        def __enter__(self): return DummyConn()
        def __exit__(self, *args): pass
    class DummyEngine:
        def connect(self): return DummyCtx()
        def begin(self): return DummyCtx()

    monkeypatch.setattr(ats_reverse, "get_engine", lambda: DummyEngine())
    monkeypatch.setattr(ats_reverse, "check_ats_exists", lambda *args, **kwargs: False)
    monkeypatch.setattr(ats_reverse, "get_or_create_placeholder_company", lambda *args, **kwargs: "dummy-uuid")

    def mock_insert(conn, **kwargs):
        if kwargs.get("ats_slug") == "fail1":
            # Symulujemy błąd naruszenia unikalności / błąd bazy
            raise RuntimeError("Simulated DB IntegrityError")
        return True

    monkeypatch.setattr(ats_reverse, "insert_discovered_company_ats", mock_insert)

    metrics = ats_reverse.run_ats_reverse_discovery()

    # The loop tests all 3 slugs. The second one fails during insert, but it doesn't break the whole script,
    # allowing ok1 and ok2 to be logged as successfully fetched ATS (ats_inserted).
    assert metrics["slugs_tested"] == 3
    assert metrics["ats_detected"] == 3
    assert metrics["ats_inserted"] == 2
    assert metrics["ats_duplicates"] == 0