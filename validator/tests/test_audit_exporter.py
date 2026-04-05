import json
from unittest.mock import MagicMock, patch


def test_run_audit_export_skipped_when_no_bucket(monkeypatch):
    monkeypatch.delenv("INTERNAL_AUDIT_BUCKET", raising=False)
    from app.workers.audit_exporter import run_audit_export

    result = run_audit_export()
    assert result["status"] == "skipped"
    assert result["reason"] == "no_bucket_configured"


@patch("app.workers.audit_exporter.get_source_compliance_trend", return_value=[])
@patch("app.workers.audit_exporter.get_rejection_reasons_by_source", return_value=[])
@patch("app.workers.audit_exporter.get_failing_ats_integrations", return_value=[])
@patch("app.workers.audit_exporter.get_system_metrics", return_value={"jobs_total": 0})
@patch("app.workers.audit_exporter.get_audit_company_compliance_stats", return_value=[])
@patch("app.workers.audit_exporter.get_audit_source_compliance_stats_last_7d", return_value=[])
@patch("google.cloud.storage.Client")
def test_run_audit_export_uploads_snapshot_only_when_no_public_bucket(
    mock_storage_client, mock_7d, mock_company, mock_metrics, mock_ats, mock_reasons, mock_trend, monkeypatch
):
    monkeypatch.setenv("INTERNAL_AUDIT_BUCKET", "test-audit-bucket")
    monkeypatch.delenv("PUBLIC_FEED_BUCKET", raising=False)

    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage_client.return_value.bucket.return_value = mock_bucket

    from app.workers.audit_exporter import run_audit_export

    result = run_audit_export()

    assert result["status"] == "ok"
    mock_bucket.blob.assert_called_once_with("audit_snapshot.json")
    call = mock_blob.upload_from_string.call_args
    assert call.kwargs.get("content_type") == "application/json"
    snapshot = json.loads(call.args[0])
    assert "generated_at" in snapshot
    assert snapshot["metrics"] == {"jobs_total": 0}
    assert snapshot["ats_health"] == {"days_threshold": 3, "items": []}


@patch(
    "app.workers.audit_exporter.get_source_compliance_trend",
    return_value=[
        {
            "week": "2026-03-30",
            "source": "greenhouse",
            "total": 10,
            "approved": 8,
            "rejected": 2,
            "approved_ratio_pct": 80.0,
        }
    ],
)
@patch("app.workers.audit_exporter.get_rejection_reasons_by_source", return_value=[])
@patch("app.workers.audit_exporter.get_failing_ats_integrations", return_value=[{"company_ats_id": "1"}])
@patch("app.workers.audit_exporter.get_system_metrics", return_value={"jobs_total": 123})
@patch("app.workers.audit_exporter.get_audit_company_compliance_stats", return_value=[])
@patch("app.workers.audit_exporter.get_audit_source_compliance_stats_last_7d", return_value=[])
@patch("google.cloud.storage.Client")
def test_run_audit_export_ignores_public_bucket_and_uploads_snapshot_only(
    mock_storage_client, mock_7d, mock_company, mock_metrics, mock_ats, mock_reasons, mock_trend, monkeypatch
):
    monkeypatch.setenv("INTERNAL_AUDIT_BUCKET", "test-audit-bucket")
    monkeypatch.setenv("PUBLIC_FEED_BUCKET", "public-bucket")

    mock_private_blob = MagicMock()
    mock_private_bucket = MagicMock()
    mock_private_bucket.blob.return_value = mock_private_blob
    mock_storage_client.return_value.bucket.return_value = mock_private_bucket

    from app.workers.audit_exporter import run_audit_export

    result = run_audit_export()

    assert result["status"] == "ok"

    snapshot_call = mock_private_blob.upload_from_string.call_args
    snapshot = json.loads(snapshot_call.args[0])
    assert snapshot["metrics"] == {"jobs_total": 123}
    assert snapshot["ats_health"] == {"days_threshold": 3, "items": [{"company_ats_id": "1"}]}
    mock_private_blob.generate_signed_url.assert_not_called()


@patch("app.workers.audit_exporter.get_source_compliance_trend", side_effect=Exception("db down"))
@patch("google.cloud.storage.Client")
def test_run_audit_export_returns_error_on_exception(mock_storage_client, mock_trend, monkeypatch):
    monkeypatch.setenv("INTERNAL_AUDIT_BUCKET", "test-audit-bucket")

    from app.workers.audit_exporter import run_audit_export

    result = run_audit_export()

    assert result["status"] == "error"
    assert "db down" in result["error"]
    mock_storage_client.return_value.bucket.return_value.blob.return_value.upload_from_string.assert_not_called()
