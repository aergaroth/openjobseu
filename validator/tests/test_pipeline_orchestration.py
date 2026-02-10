from app.workers import post_ingestion
from app.workers import tick_pipeline


def test_post_ingestion_runs_steps_in_order(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(post_ingestion, "init_db", lambda: calls.append("init_db"))
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

    assert calls == ["init_db", "availability", "lifecycle"]


def test_tick_pipeline_runs_post_ingestion_once(monkeypatch):
    post_calls = {"count": 0}

    def handler():
        return {"actions": ["remotive_ingested:1"]}

    def fake_post_ingestion():
        post_calls["count"] += 1

    monkeypatch.setattr(tick_pipeline, "run_post_ingestion", fake_post_ingestion)

    result = tick_pipeline.run_tick_pipeline(
        ingestion_sources=["remotive"],
        ingestion_handlers={"remotive": handler},
    )

    assert post_calls["count"] == 1
    assert result["actions"] == ["remotive_ingested:1"]
    assert "metrics" in result
    assert "tick_duration_ms" in result["metrics"]
    assert result["metrics"]["ingestion"]["sources_total"] == 1
    assert "remotive" in result["metrics"]["ingestion"]["per_source"]


def test_tick_pipeline_aggregates_per_source_metrics(monkeypatch):
    def ok_handler():
        return {
            "actions": ["remotive_ingested:3"],
            "metrics": {
                "source": "remotive",
                "status": "ok",
                "raw_count": 10,
                "persisted_count": 3,
                "skipped_count": 7,
                "duration_ms": 25,
            },
        }

    def failed_handler():
        raise RuntimeError("source down")

    monkeypatch.setattr(tick_pipeline, "run_post_ingestion", lambda: None)

    result = tick_pipeline.run_tick_pipeline(
        ingestion_sources=["remotive", "remoteok", "unknown"],
        ingestion_handlers={
            "remotive": ok_handler,
            "remoteok": failed_handler,
        },
    )

    ingestion_metrics = result["metrics"]["ingestion"]

    assert ingestion_metrics["sources_total"] == 3
    assert ingestion_metrics["sources_ok"] == 1
    assert ingestion_metrics["sources_failed"] == 1
    assert ingestion_metrics["sources_unknown"] == 1
    assert ingestion_metrics["raw_count"] == 10
    assert ingestion_metrics["persisted_count"] == 3
    assert ingestion_metrics["skipped_count"] == 7
    assert ingestion_metrics["per_source"]["remotive"]["status"] == "ok"
    assert ingestion_metrics["per_source"]["remoteok"]["status"] == "failed"
    assert ingestion_metrics["per_source"]["unknown"]["status"] == "unknown"
