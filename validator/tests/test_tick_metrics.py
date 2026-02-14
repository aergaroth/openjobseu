from app.workers import tick


def test_local_tick_returns_runtime_metrics(monkeypatch):
    monkeypatch.setattr(
        tick,
        "load_local_jobs",
        lambda _: [{"id": "1"}, {"id": "2"}, {"id": "3"}],
    )
    monkeypatch.setattr(tick, "run_post_ingestion", lambda: None)

    result = tick.run_tick()

    assert result["actions"] == ["local_ingested:3"]
    assert "metrics" in result
    assert result["metrics"]["tick_duration_ms"] >= 0
    assert result["metrics"]["ingestion"]["sources_total"] == 1
    assert result["metrics"]["ingestion"]["sources_ok"] == 1
    assert result["metrics"]["ingestion"]["raw_count"] == 3
    assert result["metrics"]["ingestion"]["per_source"]["local"]["status"] == "ok"
    assert (
        result["metrics"]["ingestion"]["per_source"]["local"]["policy"]["rejected_total"]
        == 0
    )


def test_local_tick_reports_failed_ingestion_metrics(monkeypatch):
    def broken_loader(_):
        raise RuntimeError("broken")

    monkeypatch.setattr(tick, "load_local_jobs", broken_loader)
    monkeypatch.setattr(tick, "run_post_ingestion", lambda: None)

    result = tick.run_tick()

    assert result["actions"] == ["local_ingestion_failed"]
    assert result["metrics"]["ingestion"]["sources_failed"] == 1
    assert result["metrics"]["ingestion"]["per_source"]["local"]["status"] == "failed"
    assert (
        result["metrics"]["ingestion"]["per_source"]["local"]["policy"]["rejected_total"]
        == 0
    )
