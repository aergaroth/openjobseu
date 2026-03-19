from app.workers.ingestion import log_helpers
from app.domain.taxonomy.enums import RemoteClass


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
        source="greenhouse:acme",
        phase="fetch",
        raw_count=7,
    )

    assert len(debug_calls) == 1
    assert len(info_calls) == 0

    msg = debug_calls[0]["message"]
    extra = debug_calls[0]["extra"]

    assert isinstance(msg, str)
    assert extra["component"] == "ingestion"
    assert extra["source"] == "greenhouse:acme"
    assert extra["phase"] == "fetch"
    assert extra["raw_count"] == 7


def test_ingestion_summary_logs_on_info(monkeypatch):
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
        source="lever:acme",
        phase="ingestion_summary",
        fetched=4,
        normalized=3,
        accepted=2,
        rejected_policy=1,
        remote_model_counts={
            RemoteClass.REMOTE_ONLY.value: 2,
            "remote_but_geo_restricted": 1,
            RemoteClass.NON_REMOTE.value: 3,
            RemoteClass.UNKNOWN.value: 4,
        },
        duration_ms=10,
    )

    assert len(debug_calls) == 0
    assert len(info_calls) == 1

    msg = info_calls[0]["message"]
    extra = info_calls[0]["extra"]

    # Sprawdzamy tylko semantykę message
    assert msg.startswith("ingestion_summary[lever:acme]")

    # Sprawdzamy kluczowe pola, nie pełną strukturę
    assert extra["component"] == "ingestion"
    assert extra["fetched"] == 4
    assert extra["accepted"] == 2
    assert extra["rejected_policy"] == 1
    assert extra[RemoteClass.REMOTE_ONLY.value] == 2
    assert extra["remote_non_remote"] == 3
    assert extra["remote_geo_restricted"] == 1
    assert extra[f"remote_{RemoteClass.UNKNOWN.value}"] == 4
    assert extra["duration_ms"] == 10
