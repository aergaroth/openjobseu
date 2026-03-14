import pytest
from app.workers.discovery import pipeline


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

    # Upewniamy się, że wszystkie kroki zostały wywołane w odpowiedniej kolejności (błąd nie przerwał pętli)
    assert calls == ["step_1", "step_2", "step_3"]

    metrics = result["metrics"]
    assert metrics["status"] == "error"  # Ogólny status został oznaczony jako error
    assert metrics["step_one"] == {"processed": 10}
    assert metrics["step_two"]["status"] == "error"
    assert "network timeout" in metrics["step_two"]["error"]
    assert metrics["step_three"] == {"processed": 5}
    assert "duration_ms" in metrics