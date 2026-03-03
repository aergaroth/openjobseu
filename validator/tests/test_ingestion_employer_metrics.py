from app.workers.ingestion import employer


class _NoopConnectCtx:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


class _NoopEngine:
    def connect(self):
        return _NoopConnectCtx()


def test_run_employer_ingestion_reports_standardized_metrics(monkeypatch):
    monkeypatch.setattr(employer, "get_engine", lambda: _NoopEngine())
    monkeypatch.setattr(
        employer,
        "load_active_ats_companies",
        lambda _conn: [{"company_id": "c1"}, {"company_id": "c2"}],
    )

    results = iter(
        [
            {
                "fetched": 5,
                "normalized_count": 4,
                "accepted": 3,
                "skipped": 1,
                "rejected_policy_count": 1,
                "rejected_by_reason": {
                    "non_remote": 1,
                    "geo_restriction": 0,
                },
                "remote_model_counts": {
                    "remote_only": 2,
                    "remote_but_geo_restricted": 1,
                    "non_remote": 1,
                    "unknown": 0,
                },
                "hard_geo_rejected_count": 0,
            },
            {
                "fetched": 0,
                "normalized_count": 0,
                "accepted": 0,
                "skipped": 0,
                "error": "invalid_ats_slug",
            },
        ]
    )
    monkeypatch.setattr(employer, "ingest_company", lambda _company: next(results))

    result = employer.run_employer_ingestion()
    metrics = result["metrics"]

    assert result["actions"] == ["employer_ingestion_completed"]
    assert metrics["source"] == "employer_ing"
    assert metrics["status"] == "ok"
    assert metrics["fetched_count"] == 5
    assert metrics["normalized_count"] == 4
    assert metrics["accepted_count"] == 3
    assert metrics["raw_count"] == 5
    assert metrics["persisted_count"] == 3
    assert metrics["skipped_count"] == 1
    assert metrics["policy_rejected_total"] == 1
    assert metrics["policy_rejected_by_reason"]["non_remote"] == 1
    assert metrics["policy_rejected_by_reason"]["geo_restriction"] == 0
    assert metrics["remote_model_counts"] == {
        "remote_only": 2,
        "remote_but_geo_restricted": 1,
        "non_remote": 1,
        "unknown": 0,
    }
    assert metrics["companies_processed"] == 2
    assert metrics["companies_failed"] == 1
    assert metrics["companies_invalid_slug"] == 1
    assert metrics["accepted_jobs"] == 3
    assert metrics["hard_geo_rejected_count"] == 0
