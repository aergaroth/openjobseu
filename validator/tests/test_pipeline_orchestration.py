from app.workers import post_ingestion
from app.workers import tick_pipeline


def test_post_ingestion_runs_steps_in_order(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        post_ingestion,
        "run_availability_pipeline",
        lambda: calls.append("availability"),
    )
    monkeypatch.setattr(
        post_ingestion,
        "run_lifecycle_pipeline",
        lambda: calls.append("lifecycle"),
    )

    post_ingestion.run_post_ingestion()

    assert calls == ["availability", "lifecycle"]


def test_post_ingestion_logs_single_summary(monkeypatch):
    info_calls = []

    monkeypatch.setattr(
        post_ingestion,
        "run_availability_pipeline",
        lambda: {"checked": 5, "expired": 2, "unreachable": 1},
    )
    monkeypatch.setattr(post_ingestion, "run_lifecycle_pipeline", lambda: None)
    monkeypatch.setattr(
        post_ingestion.logger,
        "info",
        lambda message, extra=None: info_calls.append(
            {"message": message, "extra": extra or {}}
        ),
    )

    post_ingestion.run_post_ingestion()

    assert len(info_calls) == 1
    summary = info_calls[0]
    assert summary["message"] == "post_ingestion_summary"
    assert summary["extra"]["phase"] == "post_ingestion_summary"
    assert summary["extra"]["availability_checked"] == 5
    assert summary["extra"]["expired"] == 2
    assert summary["extra"]["unreachable"] == 1
    assert summary["extra"]["duration_ms"] >= 0


def test_tick_pipeline_runs_employer_ingestion_then_post_ingestion(monkeypatch):
    order = []

    def _fake_employer_ingestion():
        order.append("ingestion")
        return {
            "actions": ["employer_ingestion_completed"],
            "metrics": {
                "source": "employer_ing",
                "status": "ok",
                "raw_count": 2,
                "persisted_count": 1,
                "skipped_count": 1,
                "duration_ms": 5,
            },
        }

    def _fake_post_ingestion():
        order.append("post_ingestion")

    info_calls = []
    monkeypatch.setattr(tick_pipeline, "run_employer_ingestion", _fake_employer_ingestion)
    monkeypatch.setattr(tick_pipeline, "run_post_ingestion", _fake_post_ingestion)
    monkeypatch.setattr(
        tick_pipeline.logger,
        "info",
        lambda message, extra=None: info_calls.append(
            {"message": message, "extra": extra or {}}
        ),
    )

    result = tick_pipeline.run_tick_pipeline()

    assert order == ["ingestion", "post_ingestion"]
    assert result["actions"] == ["employer_ingestion_completed"]
    assert result["metrics"]["ingestion"]["source"] == "employer_ing"
    assert result["metrics"]["ingestion"]["persisted_count"] == 1

    finish_calls = [
        call
        for call in info_calls
        if call["extra"].get("phase") == "tick_finished"
    ]
    assert len(finish_calls) == 1
    finish_log = finish_calls[0]
    assert finish_log["message"] == "tick_finished"
    assert finish_log["extra"]["total_duration_ms"] >= 0
    assert finish_log["extra"]["sources_ok"] == 1
    assert finish_log["extra"]["sources_failed"] == 0
    assert finish_log["extra"]["persisted_count"] == 1
