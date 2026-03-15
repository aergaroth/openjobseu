from app.workers import pipeline


def test_pipeline_runs_steps_in_order(monkeypatch):
    order: list[str] = []

    monkeypatch.setattr(
        pipeline,
        "run_employer_ingestion",
        lambda: order.append("ingestion") or {"actions": [], "metrics": {"status": "ok", "persisted_count": 0}},
    )
    monkeypatch.setattr(
        pipeline,
        "run_lifecycle_pipeline",
        lambda: order.append("lifecycle"),
    )
    monkeypatch.setattr(
        pipeline,
        "run_availability_pipeline",
        lambda: order.append("availability"),
    )
    monkeypatch.setattr(
        pipeline,
        "run_market_metrics_worker",
        lambda: order.append("market_metrics"),
    )
    monkeypatch.setattr(
        pipeline,
        "run_maintenance_pipeline",
        lambda: order.append("maintenance"),
    )

    pipeline.run_pipeline()

    assert order == ["ingestion", "lifecycle", "availability", "market_metrics", "maintenance"]
    
    order.clear()
    pipeline.run_pipeline("ingestion")
    assert order == ["ingestion"]
    
    order.clear()
    pipeline.run_pipeline("maintenance")
    assert order == ["lifecycle", "availability", "market_metrics", "maintenance"]


def test_pipeline_orchestration_full_flow(monkeypatch):
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

    def _fake_lifecycle():
        order.append("lifecycle")

    def _fake_availability():
        order.append("availability")
        return {"metrics": {"checked": 5, "expired": 2, "unreachable": 1}}

    def _fake_market_metrics():
        order.append("market_metrics")
        return {"metrics": {"component": "market_metrics", "jobs_created": 10}}

    def _fake_maintenance():
        order.append("maintenance")
        return {"metrics": {"component": "maintenance", "job_stats_updated": 5, "scores_updated": 5}}

    info_calls = []
    monkeypatch.setattr(pipeline, "run_employer_ingestion", _fake_employer_ingestion)
    monkeypatch.setattr(pipeline, "run_lifecycle_pipeline", _fake_lifecycle)
    monkeypatch.setattr(pipeline, "run_availability_pipeline", _fake_availability)
    monkeypatch.setattr(pipeline, "run_market_metrics_worker", _fake_market_metrics)
    monkeypatch.setattr(pipeline, "run_maintenance_pipeline", _fake_maintenance)
    monkeypatch.setattr(
        pipeline.logger,
        "info",
        lambda message, extra=None: info_calls.append(
            {"message": message, "extra": extra or {}}
        ),
    )

    result = pipeline.run_pipeline()

    assert order == ["ingestion", "lifecycle", "availability", "market_metrics", "maintenance"]
    assert result["actions"] == ["employer_ingestion_completed"]
    assert result["metrics"]["ingestion"]["source"] == "employer_ing"
    assert result["metrics"]["availability"]["checked"] == 5
    assert result["metrics"]["market_metrics"]["component"] == "market_metrics"

    finish_calls = [
        call
        for call in info_calls
        if call["extra"].get("phase") == "tick_finished"
    ]
    assert len(finish_calls) == 1
    finish_log = finish_calls[0]
    assert finish_log["message"] == "tick_finished"
    assert finish_log["extra"]["persisted_count"] == 1
