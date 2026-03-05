from app.workers import tick_pipeline


def test_tick_pipeline_returns_runtime_metrics(monkeypatch):
    monkeypatch.setattr(
        tick_pipeline,
        "run_employer_ingestion",
        lambda: {
            "actions": ["employer_ingestion_completed"],
            "metrics": {
                "source": "employer_ing",
                "status": "ok",
                "raw_count": 3,
                "persisted_count": 2,
                "skipped_count": 1,
            },
        },
    )
    monkeypatch.setattr(tick_pipeline, "run_post_ingestion", lambda: None)

    result = tick_pipeline.run_tick_pipeline()

    assert result["actions"] == ["employer_ingestion_completed"]
    assert "metrics" in result
    assert result["metrics"]["tick_duration_ms"] >= 0
    assert result["metrics"]["ingestion"]["source"] == "employer_ing"
    assert result["metrics"]["ingestion"]["raw_count"] == 3
    assert result["metrics"]["ingestion"]["persisted_count"] == 2
    assert result["metrics"]["ingestion"]["skipped_count"] == 1


def test_tick_pipeline_runs_post_ingestion_on_ingestion_failure(monkeypatch):
    post_calls = {"count": 0}

    def _broken_ingestion():
        raise RuntimeError("boom")

    def _fake_post_ingestion():
        post_calls["count"] += 1

    monkeypatch.setattr(tick_pipeline, "run_employer_ingestion", _broken_ingestion)
    monkeypatch.setattr(tick_pipeline, "run_post_ingestion", _fake_post_ingestion)

    result = tick_pipeline.run_tick_pipeline()

    assert result["actions"] == []
    assert result["metrics"]["ingestion"]["status"] == "failed"
    assert post_calls["count"] == 1
