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
    assert "remote_model_totals" in result["metrics"]["ingestion"]
    totals = result["metrics"]["ingestion"]["remote_model_totals"]
    for key in ("remote_only", "remote_but_geo_restricted", "non_remote", "unknown"):
        assert key in totals
        assert isinstance(totals[key], int)
    assert result["metrics"]["ingestion"]["per_source"]["local"]["status"] == "ok"
    assert "remote_model" in result["metrics"]["ingestion"]["per_source"]["local"]
    rm = result["metrics"]["ingestion"]["per_source"]["local"]["remote_model"]
    assert set(rm.keys()) == {
        "remote_only",
        "remote_but_geo_restricted",
        "non_remote",
        "unknown",
    }
    for key in rm:
        assert isinstance(rm[key], int)
    assert (
        "remote_model_counts"
        in result["metrics"]["ingestion"]["per_source"]["local"]
    )
    rm_counts = result["metrics"]["ingestion"]["per_source"]["local"]["remote_model_counts"]
    assert set(rm_counts.keys()) == {
        "remote_only",
        "remote_but_geo_restricted",
        "non_remote",
        "unknown",
    }
    for key in rm_counts:
        assert isinstance(rm_counts[key], int)
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
    assert "remote_model_totals" in result["metrics"]["ingestion"]
    totals = result["metrics"]["ingestion"]["remote_model_totals"]
    for key in ("remote_only", "remote_but_geo_restricted", "non_remote", "unknown"):
        assert key in totals
        assert isinstance(totals[key], int)
    assert result["metrics"]["ingestion"]["per_source"]["local"]["status"] == "failed"
    assert "remote_model" in result["metrics"]["ingestion"]["per_source"]["local"]
    rm = result["metrics"]["ingestion"]["per_source"]["local"]["remote_model"]
    assert set(rm.keys()) == {
        "remote_only",
        "remote_but_geo_restricted",
        "non_remote",
        "unknown",
    }
    for key in rm:
        assert isinstance(rm[key], int)
    assert (
        "remote_model_counts"
        in result["metrics"]["ingestion"]["per_source"]["local"]
    )
    rm_counts = result["metrics"]["ingestion"]["per_source"]["local"]["remote_model_counts"]
    assert set(rm_counts.keys()) == {
        "remote_only",
        "remote_but_geo_restricted",
        "non_remote",
        "unknown",
    }
    for key in rm_counts:
        assert isinstance(rm_counts[key], int)
    assert (
        result["metrics"]["ingestion"]["per_source"]["local"]["policy"]["rejected_total"]
        == 0
    )
