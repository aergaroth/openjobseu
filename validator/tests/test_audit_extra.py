from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)


def test_audit_panel_oserror(monkeypatch):
    import app.api.audit as audit_api

    monkeypatch.setattr(audit_api, "_load_audit_panel_html", MagicMock(side_effect=OSError("File not found")))
    res = client.get("/internal/audit")
    assert res.status_code == 500

    monkeypatch.setattr(audit_api, "_load_audit_panel_js", MagicMock(side_effect=OSError("File not found")))
    res = client.get("/internal/audit/script.js")
    assert res.status_code == 500

    monkeypatch.setattr(audit_api, "_load_audit_panel_css", MagicMock(side_effect=OSError("File not found")))
    res = client.get("/internal/audit/style.css")
    assert res.status_code == 500


def test_audit_panel_local_runtime(monkeypatch):
    import app.api.audit as audit_api

    monkeypatch.setenv("APP_RUNTIME", "local")
    mock_path = MagicMock()
    mock_path.read_text.return_value = "local content"

    monkeypatch.setattr(audit_api, "AUDIT_PANEL_PATH", mock_path)
    monkeypatch.setattr(audit_api, "AUDIT_PANEL_JS_PATH", mock_path)
    monkeypatch.setattr(audit_api, "AUDIT_PANEL_CSS_PATH", mock_path)

    assert "local content" in client.get("/internal/audit").text
    assert "local content" in client.get("/internal/audit/script.js").text
    assert "local content" in client.get("/internal/audit/style.css").text


@patch("app.api.audit.get_engine")
@patch("app.api.audit.deactivate_ats_integration")
def test_api_deactivate_ats(mock_deactivate, mock_get_engine):
    res = client.post("/internal/audit/ats-deactivate/my-ats-id")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "company_ats_id": "my-ats-id"}
    mock_deactivate.assert_called_once()


@patch("app.api.audit.get_ats_integration_by_id")
@patch("app.api.audit.get_engine")
def test_api_force_sync_ats_no_adapter(mock_get_engine, mock_get_integration, monkeypatch):
    mock_get_integration.return_value = {
        "ats_provider": "unknown_provider",
        "ats_slug": "x",
        "company_id": "y",
        "legal_name": "z",
    }
    res = client.post("/internal/audit/ats-force-sync/fake_id")
    assert res.status_code == 400
    assert "No adapter found" in res.json()["detail"]


@patch("app.api.audit.get_ats_integration_by_id")
@patch("app.api.audit.get_engine")
def test_api_force_sync_ats_fetch_exception(mock_get_engine, mock_get_integration, monkeypatch):
    mock_get_integration.return_value = {"ats_provider": "lever", "ats_slug": "x", "company_id": "y", "legal_name": "z"}
    res = client.post("/internal/audit/ats-force-sync/fake_id")
    assert res.status_code == 500
