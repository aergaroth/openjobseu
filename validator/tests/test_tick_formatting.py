from app.utils.tick_formatting import format_tick_summary


def test_tick_summary_renders_source_row_for_flat_ingestion_metrics():
    payload = {
        "mode": "prod",
        "metrics": {
            "tick_duration_ms": 1234,
            "ingestion": {
                "source": "employer_ing",
                "raw_count": 10,
                "persisted_count": 7,
                "skipped_count": 3,
                "policy_rejected_total": 3,
                "policy_rejected_by_reason": {
                    "non_remote": 2,
                    "geo_restriction": 1,
                },
                "remote_model_counts": {
                    "remote_only": 7,
                    "remote_but_geo_restricted": 1,
                    "unknown": 2,
                },
                "duration_ms": 999,
            },
        },
    }

    text = format_tick_summary(payload)

    assert "employer_ing" in text
    assert "raw=10  persisted=7  skipped=3  duration=1234 ms" in text


def test_tick_summary_keeps_per_source_metrics_when_provided():
    payload = {
        "mode": "prod",
        "metrics": {
            "tick_duration_ms": 500,
            "ingestion": {
                "raw_count": 3,
                "persisted_count": 2,
                "skipped_count": 1,
                "per_source": {
                    "source_a": {
                        "raw_count": 2,
                        "persisted_count": 1,
                        "policy": {"rejected_total": 1, "by_reason": {"non_remote": 1}},
                        "remote_model_counts": {"remote_only": 1, "unknown": 1},
                        "duration_ms": 100,
                    },
                    "source_b": {
                        "raw_count": 1,
                        "persisted_count": 1,
                        "policy": {"rejected_total": 0, "by_reason": {}},
                        "remote_model_counts": {"remote_only": 1},
                        "duration_ms": 50,
                    },
                },
            },
        },
    }

    text = format_tick_summary(payload)

    assert "source_a" in text
    assert "source_b" in text
    assert "raw=3  persisted=2  skipped=1  duration=500 ms" in text
