import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path

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
        [],  # Scenariusz 1: Pusta lista (zabezpieczenie na wypadek braku ofert)
        [  # Scenariusz 2: Jedna oferta z wyzerowanymi godzinami
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
        [  # Scenariusz 3: Wiele ofert w różnych stanach z nietypowymi godzinami
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
    """Test pełnego eksportu HTML/CSS oraz wygenerowanego feed.json do zmockowanego GCS"""
    # 1. Ustawienie środowiska i udawanego Bucketa
    monkeypatch.setenv("PUBLIC_FEED_BUCKET", "test-bucket.local")

    mock_client_instance = MagicMock()
    mock_storage_client.return_value = mock_client_instance

    mock_bucket = MagicMock()
    mock_client_instance.bucket.return_value = mock_bucket

    mock_bucket.get_blob.return_value = None  # Symulacja braku pliku w GCS (wymusi upload)
    # Śledzimy tworzone obiekty Blob w słowniku, by móc sprawdzić ich właściwości
    created_blobs = {}

    def make_mock_blob(blob_name):
        created_blobs[blob_name] = MagicMock()
        return created_blobs[blob_name]

    mock_bucket.blob.side_effect = make_mock_blob

    # 2. Utworzenie tymczasowego katalogu ze statycznymi plikami (imitacja katalogu /frontend)
    fake_frontend_dir = tmp_path / "frontend"
    fake_frontend_dir.mkdir()
    (fake_frontend_dir / "index.html").write_text("<h1>Test</h1>", encoding="utf-8")
    (fake_frontend_dir / "style.css").write_text("body { color: red; }", encoding="utf-8")

    monkeypatch.setattr(frontend_exporter, "FRONTEND_DIR", fake_frontend_dir)

    # 3. Zmockowanie zapytania do bazy listą zdefiniowaną z parametryzacji
    monkeypatch.setattr(frontend_exporter, "get_jobs", lambda **kwargs: jobs_payload)

    # 4. Wykonanie funkcji
    result = run_frontend_export(sync_assets=True)

    # 5. Asercje
    assert result["status"] == "ok"
    assert result["exported_jobs"] == len(jobs_payload)
    assert result["uploaded_files"] == 3  # (index.html, style.css, feed.json)

    # Sprawdzenie, czy faktycznie próbowano wgrać feed.json oraz pliki HTML
    mock_bucket.blob.assert_any_call("feed.json")
    mock_bucket.blob.assert_any_call("index.html")
    mock_bucket.blob.assert_any_call("style.css")

    # 6. Weryfikacja poprawności nagłówków Cache-Control oraz wgrania zawartości dla konkretnych plików
    assert created_blobs["feed.json"].cache_control == "public, max-age=300"
    assert created_blobs["feed.json"].upload_from_string.called

    assert created_blobs["index.html"].cache_control == "public, max-age=3600"
    assert created_blobs["index.html"].upload_from_string.called
    assert created_blobs["style.css"].cache_control == "public, max-age=3600"

    # 7. Weryfikacja struktury wygenerowanego i wgranego JSON-a
    upload_call_args = created_blobs["feed.json"].upload_from_string.call_args
    uploaded_json_string = upload_call_args[0][0]

    # Dekodujemy zrzuconego stringa z powrotem do słownika
    uploaded_data = json.loads(uploaded_json_string)

    assert "meta" in uploaded_data
    assert uploaded_data["meta"]["count"] == len(jobs_payload)

    assert "jobs" in uploaded_data
    assert len(uploaded_data["jobs"]) == len(jobs_payload)

    # Jeżeli mamy oferty w payloadzie testowym, upewnijmy się co do pierwszej z nich
    if jobs_payload:
        assert uploaded_data["jobs"][0]["id"] == jobs_payload[0]["job_id"]
        expected_date = jobs_payload[0]["first_seen_at"].isoformat().replace("+00:00", "Z")
        assert uploaded_data["jobs"][0]["first_seen_at"] == expected_date


@patch("google.cloud.storage.Client")
def test_frontend_export_handles_gcs_error(mock_storage_client, monkeypatch):
    """Testuje, czy worker poprawnie wyłapuje błędy przy próbie zapisu do GCS"""
    monkeypatch.setenv("PUBLIC_FEED_BUCKET", "test-bucket.local")

    mock_client_instance = MagicMock()
    mock_storage_client.return_value = mock_client_instance

    mock_bucket = MagicMock()
    mock_client_instance.bucket.return_value = mock_bucket

    mock_blob = MagicMock()
    # KRYTYCZNE: wymuszamy rzucenie błędem przy próbie użycia upload_from_string
    mock_blob.upload_from_string.side_effect = RuntimeError("Simulated GCS Upload Failure")
    mock_bucket.blob.return_value = mock_blob

    # Izolujemy zapytania do bazy i folderu, by test skupił się tylko na wyłapaniu błędu GCS
    monkeypatch.setattr(frontend_exporter, "get_jobs", lambda **kwargs: [])
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
    monkeypatch.setattr(frontend_exporter, "get_jobs", lambda **kwargs: [])

    md5_hash = base64.b64encode(hashlib.md5(content).digest()).decode("utf-8")
    mock_existing_blob = MagicMock()
    mock_existing_blob.md5_hash = md5_hash
    mock_bucket.get_blob.return_value = mock_existing_blob

    result = run_frontend_export(sync_assets=True)

    assert result["status"] == "ok"
    assert result["uploaded_files"] == 1  # Tylko feed.json, index.html powinien zostać pominięty
