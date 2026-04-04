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


@patch("app.api.audit.get_source_compliance_trend")
def test_audit_source_trend(mock_fn):
    mock_fn.return_value = [
        {
            "week": "2026-03-30",
            "source": "greenhouse",
            "total": 20,
            "approved": 16,
            "rejected": 4,
            "approved_ratio_pct": 80.0,
        },
        {
            "week": "2026-04-06",
            "source": "greenhouse",
            "total": 10,
            "approved": 9,
            "rejected": 1,
            "approved_ratio_pct": 90.0,
        },
    ]
    res = client.get("/internal/audit/stats/source-trend")
    assert res.status_code == 200
    data = res.json()
    assert data["window_days"] == 30
    assert len(data["items"]) == 2
    assert data["items"][0]["source"] == "greenhouse"
    mock_fn.assert_called_once_with(days=30)


@patch("app.api.audit.get_source_compliance_trend")
def test_audit_source_trend_custom_days(mock_fn):
    mock_fn.return_value = []
    res = client.get("/internal/audit/stats/source-trend?days=60")
    assert res.status_code == 200
    mock_fn.assert_called_once_with(days=60)


@patch("app.api.audit.get_rejection_reasons_by_source")
def test_audit_rejection_reasons(mock_fn):
    mock_fn.return_value = [
        {"source": "greenhouse", "reason": "non_remote", "count": 12},
        {"source": "greenhouse", "reason": "non_eu_geo", "count": 5},
        {"source": "lever", "reason": "hard_geo", "count": 3},
    ]
    res = client.get("/internal/audit/stats/rejection-reasons")
    assert res.status_code == 200
    data = res.json()
    assert data["window_days"] == 30
    assert len(data["items"]) == 3
    assert data["items"][0]["reason"] == "non_remote"
    mock_fn.assert_called_once_with(days=30)


@patch("app.api.audit.get_rejection_reasons_by_source")
def test_audit_rejection_reasons_empty(mock_fn):
    mock_fn.return_value = []
    res = client.get("/internal/audit/stats/rejection-reasons")
    assert res.status_code == 200
    assert res.json()["items"] == []
