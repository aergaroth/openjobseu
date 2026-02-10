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
