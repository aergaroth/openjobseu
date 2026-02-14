from app.workers.ingestion import log_helpers


def test_fetch_phase_logs_on_debug(monkeypatch):
    debug_calls = []
    info_calls = []

    monkeypatch.setattr(
        log_helpers.logger,
        "debug",
        lambda message, extra=None: debug_calls.append(
            {"message": message, "extra": extra or {}}
        ),
    )
    monkeypatch.setattr(
        log_helpers.logger,
        "info",
        lambda message, extra=None: info_calls.append(
            {"message": message, "extra": extra or {}}
        ),
    )

    log_helpers.log_ingestion(
        source="remoteok",
        phase="fetch",
        raw_count=7,
    )

    assert len(debug_calls) == 1
    assert len(info_calls) == 0
    assert debug_calls[0]["message"] == "ingestion"
    assert debug_calls[0]["extra"]["component"] == "ingestion"
    assert debug_calls[0]["extra"]["source"] == "remoteok"
    assert debug_calls[0]["extra"]["phase"] == "fetch"
    assert debug_calls[0]["extra"]["raw_count"] == 7


def test_non_fetch_phase_logs_on_info(monkeypatch):
    debug_calls = []
    info_calls = []

    monkeypatch.setattr(
        log_helpers.logger,
        "debug",
        lambda message, extra=None: debug_calls.append(
            {"message": message, "extra": extra or {}}
        ),
    )
    monkeypatch.setattr(
        log_helpers.logger,
        "info",
        lambda message, extra=None: info_calls.append(
            {"message": message, "extra": extra or {}}
        ),
    )

    log_helpers.log_ingestion(
        source="remotive",
        phase="ingestion_summary",
        fetched=4,
        normalized=3,
        accepted=2,
        rejected_policy=1,
        duration_ms=10,
    )

    assert len(debug_calls) == 0
    assert len(info_calls) == 1
    assert info_calls[0]["message"] == "ingestion"
    assert info_calls[0]["extra"]["component"] == "ingestion"
    assert info_calls[0]["extra"]["source"] == "remotive"
    assert info_calls[0]["extra"]["phase"] == "ingestion_summary"
