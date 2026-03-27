from app.domain.jobs.enums import RemoteClass
from app.workers.ingestion.metrics import IngestionMetrics, _normalize_remote_model_for_metrics


def test_normalize_remote_model_for_metrics_handles_supported_variants():
    assert _normalize_remote_model_for_metrics(RemoteClass.REMOTE_ONLY.value) == RemoteClass.REMOTE_ONLY.value
    assert _normalize_remote_model_for_metrics(f"  {RemoteClass.REMOTE_ONLY.value}  ") == RemoteClass.REMOTE_ONLY.value
    assert _normalize_remote_model_for_metrics(RemoteClass.REMOTE_REGION_LOCKED.value) == "remote_but_geo_restricted"
    assert _normalize_remote_model_for_metrics("remote_but_geo_restricted") == "remote_but_geo_restricted"
    assert _normalize_remote_model_for_metrics("hybrid") == RemoteClass.NON_REMOTE.value
    assert _normalize_remote_model_for_metrics("office_first") == RemoteClass.NON_REMOTE.value
    assert _normalize_remote_model_for_metrics(None) == RemoteClass.UNKNOWN.value
    assert _normalize_remote_model_for_metrics("something-else") == RemoteClass.UNKNOWN.value


def test_ingestion_metrics_tracks_all_counters_and_returns_copies():
    metrics = IngestionMetrics(fetched_count=7)

    metrics.observe_normalized()
    metrics.observe_normalized()
    metrics.observe_accept()
    metrics.observe_skip()
    metrics.observe_rejection(RemoteClass.NON_REMOTE.value)
    metrics.observe_rejection("geo_restriction_hard")
    metrics.observe_rejection("unknown-reason")
    metrics.observe_remote_model(RemoteClass.REMOTE_ONLY.value)
    metrics.observe_remote_model("remote_but_geo_restricted")
    metrics.observe_remote_model("hybrid")
    metrics.observe_remote_model("unexpected")
    metrics.observe_salary(True)
    metrics.observe_salary(False)

    result = metrics.to_result_dict()

    assert result == {
        "fetched": 7,
        "normalized_count": 2,
        "accepted": 1,
        "skipped": 1,
        "rejected_policy_count": 2,
        "rejected_by_reason": {
            RemoteClass.NON_REMOTE.value: 1,
            "geo_restriction": 1,
        },
        "remote_model_counts": {
            RemoteClass.REMOTE_ONLY.value: 1,
            "remote_but_geo_restricted": 1,
            RemoteClass.NON_REMOTE.value: 1,
            RemoteClass.UNKNOWN.value: 1,
        },
        "hard_geo_rejected_count": 1,
        "salary_detected": 1,
        "salary_missing": 1,
    }

    result["rejected_by_reason"][RemoteClass.NON_REMOTE.value] = 999
    result["remote_model_counts"][RemoteClass.REMOTE_ONLY.value] = 999
    fresh_result = metrics.to_result_dict()

    assert fresh_result["rejected_by_reason"][RemoteClass.NON_REMOTE.value] == 1
    assert fresh_result["remote_model_counts"][RemoteClass.REMOTE_ONLY.value] == 1
