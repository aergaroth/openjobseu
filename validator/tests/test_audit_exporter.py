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
@patch("app.workers.audit_exporter.get_audit_company_compliance_stats", return_value=[])
@patch("app.workers.audit_exporter.get_audit_source_compliance_stats_last_7d", return_value=[])
@patch("google.cloud.storage.Client")
def test_run_audit_export_uploads_snapshot_only_when_no_public_bucket(
    mock_storage_client, mock_7d, mock_company, mock_reasons, mock_trend, monkeypatch
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
@patch("app.workers.audit_exporter.get_audit_company_compliance_stats", return_value=[])
@patch("app.workers.audit_exporter.get_audit_source_compliance_stats_last_7d", return_value=[])
@patch("google.auth.default")
@patch("google.auth.transport.requests.Request")
@patch("google.cloud.storage.Client")
def test_run_audit_export_publishes_meta_when_public_bucket_set(
    mock_storage_client, mock_request, mock_auth_default, mock_7d, mock_company, mock_reasons, mock_trend, monkeypatch
):
    monkeypatch.setenv("INTERNAL_AUDIT_BUCKET", "test-audit-bucket")
    monkeypatch.setenv("PUBLIC_FEED_BUCKET", "public-bucket")

    mock_credentials = MagicMock()
    mock_credentials.service_account_email = "cloudrun@project.iam.gserviceaccount.com"
    mock_credentials.token = "fake-token"
    mock_auth_default.return_value = (mock_credentials, "test-project")

    mock_private_blob = MagicMock()
    mock_private_blob.generate_signed_url.return_value = "https://signed.url/audit_snapshot.json?X-Goog-Signature=abc"
    mock_private_bucket = MagicMock()
    mock_private_bucket.blob.return_value = mock_private_blob

    mock_meta_blob = MagicMock()
    mock_public_bucket = MagicMock()
    mock_public_bucket.blob.return_value = mock_meta_blob

    def bucket_side_effect(name):
        return mock_private_bucket if name == "test-audit-bucket" else mock_public_bucket

    mock_storage_client.return_value.bucket.side_effect = bucket_side_effect

    from app.workers.audit_exporter import run_audit_export

    result = run_audit_export()

    assert result["status"] == "ok"

    # Signed URL generated with correct params
    sign_call = mock_private_blob.generate_signed_url.call_args
    assert sign_call.kwargs["method"] == "GET"
    assert sign_call.kwargs["version"] == "v4"
    assert sign_call.kwargs["service_account_email"] == "cloudrun@project.iam.gserviceaccount.com"
    assert sign_call.kwargs["access_token"] == "fake-token"

    # audit_meta.json uploaded to public bucket
    mock_public_bucket.blob.assert_called_once_with("audit_meta.json")
    assert mock_meta_blob.cache_control == "no-store"
    meta_call = mock_meta_blob.upload_from_string.call_args
    assert meta_call.kwargs.get("content_type") == "application/json"
    meta = json.loads(meta_call.args[0])
    assert "url" in meta
    assert "valid_until" in meta
    assert "signed.url" in meta["url"]


@patch("app.workers.audit_exporter.get_source_compliance_trend", side_effect=Exception("db down"))
@patch("google.cloud.storage.Client")
def test_run_audit_export_returns_error_on_exception(mock_storage_client, mock_trend, monkeypatch):
    monkeypatch.setenv("INTERNAL_AUDIT_BUCKET", "test-audit-bucket")

    from app.workers.audit_exporter import run_audit_export

    result = run_audit_export()

    assert result["status"] == "error"
    assert "db down" in result["error"]
    mock_storage_client.return_value.bucket.return_value.blob.return_value.upload_from_string.assert_not_called()
