import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.workers import frontend_exporter
from app.workers.frontend_exporter import run_frontend_export


def test_frontend_export_skipped_when_no_bucket(monkeypatch):
    """Test sprawdza, czy worker pomija pracę, gdy nie ma skonfigurowanego bucketa GCS"""
    monkeypatch.delenv("PUBLIC_FEED_BUCKET", raising=False)
    result = run_frontend_export()
    assert result["status"] == "skipped"
    assert result["reason"] == "no_bucket_configured"


@pytest.mark.parametrize(
    "jobs_payload",
    [
        [],
        [
            {
                "job_id": "test-1",
                "title": "Backend Engineer",
                "company_name": "Acme",
                "remote_scope": "Europe",
                "source": "test_board",
                "source_url": "https://test.local",
                "first_seen_at": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
                "status": "new",
            }
        ],
        [
            {
                "job_id": "test-2",
                "title": "Frontend Engineer",
                "company_name": "Acme",
                "remote_scope": "Europe",
                "source": "test_board",
                "source_url": "https://test.local/2",
                "first_seen_at": datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc),
                "status": "active",
            },
            {
                "job_id": "test-3",
                "title": "Data Scientist",
                "company_name": "Beta",
                "remote_scope": "Worldwide",
                "source": "test_board",
                "source_url": "https://test.local/3",
                "first_seen_at": datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc),
                "status": "new",
            },
        ],
    ],
)
@patch("google.cloud.storage.Client")
def test_frontend_export_success(mock_storage_client, monkeypatch, tmp_path, jobs_payload):
    """Test pełnego eksportu assetów i wygenerowanego feed.json do zmockowanego GCS."""
    monkeypatch.setenv("PUBLIC_FEED_BUCKET", "test-bucket.local")

    mock_client_instance = MagicMock()
    mock_storage_client.return_value = mock_client_instance

    mock_bucket = MagicMock()
    mock_client_instance.bucket.return_value = mock_bucket
    mock_bucket.get_blob.return_value = None

    created_blobs = {}

    def make_mock_blob(blob_name):
        created_blobs[blob_name] = MagicMock()
        return created_blobs[blob_name]

    mock_bucket.blob.side_effect = make_mock_blob

    fake_frontend_dir = tmp_path / "frontend"
    fake_frontend_dir.mkdir()
    (fake_frontend_dir / "index.html").write_text(
        '<link rel="stylesheet" href="./style.css">\n<script src="./feed.js" defer></script>',
        encoding="utf-8",
    )
    (fake_frontend_dir / "style.css").write_text("body { color: red; }", encoding="utf-8")
    (fake_frontend_dir / "feed.js").write_text("console.log('feed');", encoding="utf-8")

    monkeypatch.setattr(frontend_exporter, "FRONTEND_DIR", fake_frontend_dir)
    monkeypatch.setattr("storage.repositories.jobs_repository.get_jobs", lambda **kwargs: jobs_payload)

    result = run_frontend_export(sync_assets=True, asset_version="release-123")

    assert result["status"] == "ok"
    assert result["exported_jobs"] == len(jobs_payload)
    assert (
        result["uploaded_files"] == 12
    )  # 3 assets + 1 feed.json + 6 chart SVGs + 1 market-stats.json + 1 market-segments.json
    assert result["synced_assets"] is True
    assert result["exported_feed"] is True
    assert result["asset_version"] == "release-123"

    mock_bucket.blob.assert_any_call("feed.json")
    mock_bucket.blob.assert_any_call("index.html")
    mock_bucket.blob.assert_any_call("style.css")
    mock_bucket.blob.assert_any_call("feed.js")

    assert created_blobs["feed.json"].cache_control == "public, max-age=300"
    assert created_blobs["index.html"].cache_control == "public, max-age=300"
    assert created_blobs["style.css"].cache_control == "public, max-age=31536000, immutable"
    assert created_blobs["feed.js"].cache_control == "public, max-age=31536000, immutable"

    uploaded_index = created_blobs["index.html"].upload_from_string.call_args[0][0].decode("utf-8")
    assert "./style.css?v=release-123" in uploaded_index
    assert "./feed.js?v=release-123" in uploaded_index

    uploaded_json_string = created_blobs["feed.json"].upload_from_string.call_args[0][0]
    uploaded_data = json.loads(uploaded_json_string)

    assert "meta" in uploaded_data
    assert uploaded_data["meta"]["count"] == len(jobs_payload)
    assert "jobs" in uploaded_data
    assert len(uploaded_data["jobs"]) == len(jobs_payload)

    if jobs_payload:
        assert uploaded_data["jobs"][0]["id"] == jobs_payload[0]["job_id"]
        expected_date = jobs_payload[0]["first_seen_at"].isoformat().replace("+00:00", "Z")
        assert uploaded_data["jobs"][0]["first_seen_at"] == expected_date


@patch("google.cloud.storage.Client")
def test_frontend_export_handles_gcs_error(mock_storage_client, monkeypatch):
    """Testuje, czy worker poprawnie wyłapuje błędy przy próbie zapisu do GCS."""
    monkeypatch.setenv("PUBLIC_FEED_BUCKET", "test-bucket.local")

    mock_client_instance = MagicMock()
    mock_storage_client.return_value = mock_client_instance

    mock_bucket = MagicMock()
    mock_client_instance.bucket.return_value = mock_bucket

    mock_blob = MagicMock()
    mock_blob.upload_from_string.side_effect = RuntimeError("Simulated GCS Upload Failure")
    mock_bucket.blob.return_value = mock_blob

    monkeypatch.setattr("storage.repositories.jobs_repository.get_jobs", lambda **kwargs: [])
    monkeypatch.setattr(frontend_exporter, "FRONTEND_DIR", Path("/tmp/nonexistent"))

    result = run_frontend_export()

    assert result["status"] == "error"
    assert "Simulated GCS Upload Failure" in result["error"]


@patch("google.cloud.storage.Client")
def test_frontend_export_skips_unchanged_assets(mock_storage_client, monkeypatch, tmp_path):
    import base64
    import hashlib

    monkeypatch.setenv("PUBLIC_FEED_BUCKET", "test-bucket.local")
    mock_bucket = MagicMock()
    mock_storage_client.return_value.bucket.return_value = mock_bucket

    fake_frontend_dir = tmp_path / "frontend"
    fake_frontend_dir.mkdir()
    content = b"<h1>Test</h1>"
    (fake_frontend_dir / "index.html").write_bytes(content)
    monkeypatch.setattr(frontend_exporter, "FRONTEND_DIR", fake_frontend_dir)
    monkeypatch.setattr("storage.repositories.jobs_repository.get_jobs", lambda **kwargs: [])

    md5_hash = base64.b64encode(hashlib.md5(content).digest()).decode("utf-8")
    mock_existing_blob = MagicMock()
    mock_existing_blob.md5_hash = md5_hash
    mock_bucket.get_blob.return_value = mock_existing_blob

    result = run_frontend_export(sync_assets=True)

    assert result["status"] == "ok"
    assert (
        result["uploaded_files"] == 9
    )  # 0 assets (skipped) + 1 feed.json + 6 chart SVGs + 1 market-stats.json + 1 market-segments.json


def test_render_asset_file_injects_release_cache_busting(tmp_path):
    index_file = tmp_path / "index.html"
    index_file.write_text(
        '<link rel="stylesheet" href="./style.css">\n<script src="./feed.js" defer></script>\n',
        encoding="utf-8",
    )

    rendered = frontend_exporter._render_asset_file(index_file, asset_version="v2.3.4")
    rendered_text = rendered.decode("utf-8")

    assert "./style.css?v=v2.3.4" in rendered_text
    assert "./feed.js?v=v2.3.4" in rendered_text


def test_run_frontend_export_can_sync_assets_without_exporting_feed(monkeypatch):
    class _Client:
        def bucket(self, name):
            assert name == "test-bucket"
            return object()

    class _StorageModule:
        @staticmethod
        def Client():
            return _Client()

    import sys
    import types

    google = types.ModuleType("google")
    cloud = types.ModuleType("google.cloud")
    storage = _StorageModule()
    cloud.storage = storage
    google.cloud = cloud
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage)

    calls = {"assets": 0, "feed": 0}

    monkeypatch.setenv("PUBLIC_FEED_BUCKET", "test-bucket")

    def fake_upload_assets(bucket, asset_version=None):
        calls["assets"] += 1
        assert asset_version == "release-123"
        return 3

    def fake_export_feed(bucket):
        calls["feed"] += 1
        return 7, 1

    monkeypatch.setattr(frontend_exporter, "_upload_frontend_assets", fake_upload_assets)
    monkeypatch.setattr(frontend_exporter, "_export_feed", fake_export_feed)

    result = frontend_exporter.run_frontend_export(
        sync_assets=True,
        asset_version="release-123",
        export_feed=False,
    )

    assert result["status"] == "ok"
    assert result["uploaded_files"] == 3
    assert result["exported_jobs"] == 0
    assert result["synced_assets"] is True
    assert result["exported_feed"] is False
    assert result["asset_version"] == "release-123"
    assert calls == {"assets": 1, "feed": 0}
