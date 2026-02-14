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


def test_post_ingestion_logs_single_summary(monkeypatch):
    info_calls = []

    monkeypatch.setattr(post_ingestion, "init_db", lambda: None)
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
    assert summary["message"] == "post_ingestion"
    assert summary["extra"]["phase"] == "post_ingestion_summary"
    assert summary["extra"]["availability_checked"] == 5
    assert summary["extra"]["expired"] == 2
    assert summary["extra"]["unreachable"] == 1
    assert summary["extra"]["duration_ms"] >= 0


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
    assert (
        result["metrics"]["ingestion"]["per_source"]["remotive"]["policy"]["rejected_total"]
        == 0
    )


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
                "policy_rejected_total": 2,
                "policy_rejected_by_reason": {
                    "non_remote": 1,
                    "geo_restriction": 1,
                },
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
    assert ingestion_metrics["per_source"]["remotive"]["policy"]["rejected_total"] == 2
    assert (
        ingestion_metrics["per_source"]["remotive"]["policy"]["by_reason"]["non_remote"]
        == 1
    )
    assert (
        ingestion_metrics["per_source"]["remotive"]["policy"]["by_reason"]["geo_restriction"]
        == 1
    )
    assert ingestion_metrics["per_source"]["remoteok"]["status"] == "failed"
    assert ingestion_metrics["per_source"]["remoteok"]["policy"]["rejected_total"] == 0
    assert ingestion_metrics["per_source"]["unknown"]["status"] == "unknown"
    assert ingestion_metrics["per_source"]["unknown"]["policy"]["rejected_total"] == 0


def test_tick_pipeline_logs_standardized_finish(monkeypatch):
    info_calls = []

    monkeypatch.setattr(
        tick_pipeline.logger,
        "info",
        lambda message, extra=None: info_calls.append(
            {"message": message, "extra": extra or {}}
        ),
    )
    monkeypatch.setattr(tick_pipeline, "run_post_ingestion", lambda: None)

    def ok_handler():
        return {
            "actions": ["remotive_ingested:1"],
            "metrics": {
                "source": "remotive",
                "status": "ok",
                "raw_count": 2,
                "persisted_count": 1,
                "skipped_count": 1,
                "duration_ms": 5,
            },
        }

    tick_pipeline.run_tick_pipeline(
        ingestion_sources=["remotive"],
        ingestion_handlers={"remotive": ok_handler},
    )

    assert not any(call["message"] == "tick pipeline started" for call in info_calls)
    assert not any(call["message"] == "starting ingestion source" for call in info_calls)

    finish_calls = [
        call
        for call in info_calls
        if call["extra"].get("phase") == "tick_finished"
    ]
    assert len(finish_calls) == 1

    finish_log = finish_calls[0]
    assert finish_log["message"] == "tick"
    assert finish_log["extra"]["total_duration_ms"] >= 0
    assert finish_log["extra"]["sources_ok"] == 1
    assert finish_log["extra"]["sources_failed"] == 0
    assert finish_log["extra"]["persisted_count"] == 1
