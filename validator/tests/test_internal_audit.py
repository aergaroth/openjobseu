from datetime import datetime, timedelta, timezone
import os
# guarantee that the database mode is configured even during module import.
os.environ.setdefault("DB_MODE", "standard")

from fastapi.testclient import TestClient

import app.api.system as system_api
import app.api.discovery as discovery_api
import app.api.audit as audit_api
from app.domain.jobs.enums import GeoClass, RemoteClass
from app.domain.compliance.classifiers.enums import ComplianceStatus
from app.main import app

client = TestClient(app)


def test_internal_audit_page_renders_html():
    response = client.get("/internal/audit")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/html")
    assert "Admin Audit Panel" in response.text


def test_internal_audit_filter_registry():
    response = client.get("/internal/audit/filters")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == ["new", "active", "stale", "expired", "unreachable"]
    assert RemoteClass.REMOTE_REGION_LOCKED.value in payload["remote_class"]
    assert RemoteClass.REMOTE_OPTIONAL.value in payload["remote_class"]
    assert "remote_but_geo_restricted" in payload["remote_class"]
    assert GeoClass.EU_EXPLICIT.value in payload["geo_class"]
    assert payload["compliance_status"] == [
        ComplianceStatus.APPROVED.value,
        ComplianceStatus.REVIEW.value,
        ComplianceStatus.REJECTED.value,
    ]
    assert payload["source"] == []


def test_internal_audit_jobs_filters_and_counts(monkeypatch):
    marker = "audit-panel-20260221"
    monkeypatch.setattr(
        audit_api,
        "get_jobs_audit",
        lambda **kwargs: {
            "total": 2,
            "limit": kwargs["limit"],
            "offset": kwargs["offset"],
            "items": [{"job_id": "audit:1"}],
            "counts": {
                "source": {"greenhouse:alpha": 2},
                "status": {"new": 1, "active": 1},
                "compliance_status": {"approved": 1, "review": 1},
            },
        },
    )
    monkeypatch.setattr(audit_api, "get_audit_source_filter_values", lambda: ["greenhouse:alpha", "lever:gamma"])

    response = client.get(
        "/internal/audit/jobs",
        params={
            "source": "greenhouse:alpha",
            "company": marker,
            "limit": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert data["limit"] == 1
    assert len(data["items"]) == 1
    assert data["counts"]["source"]["greenhouse:alpha"] == 2
    assert data["counts"]["status"]["new"] == 1
    assert data["counts"]["status"]["active"] == 1
    assert data["counts"]["compliance_status"][ComplianceStatus.APPROVED.value] == 1
    assert data["counts"]["compliance_status"][ComplianceStatus.REVIEW.value] == 1

    response_filtered = client.get(
        "/internal/audit/jobs",
        params={
            "company": f"{marker}-alpha",
            "min_compliance_score": 80,
        },
    )
    assert response_filtered.status_code == 200
    filtered = response_filtered.json()
    assert filtered["total"] == 2
    assert filtered["items"][0]["job_id"] == "audit:1"

    filters_response = client.get("/internal/audit/filters")
    assert filters_response.status_code == 200
    source_values = filters_response.json()["source"]
    assert "greenhouse:alpha" in source_values
    assert "lever:gamma" in source_values


def test_internal_audit_tick_dev_runs_tick_with_text_output(monkeypatch):
    captured = {}

    def fake_tick(force_text=False):
        captured["force_text"] = force_text
        return "tick as text"

    monkeypatch.setattr(system_api, "tick", fake_tick)

    response = client.post("/internal/audit/tick-dev")
    assert response.status_code == 200
    assert response.text == "tick as text"
    assert captured["force_text"] is True


def test_internal_audit_company_stats(monkeypatch):
    marker = "audit-company-stats-20260304"
    monkeypatch.setattr(
        audit_api,
        "get_audit_company_compliance_stats",
        lambda min_total_jobs: [
            {"legal_name": f"{marker}-high", "total_jobs": 12, "approved": 9, "rejected": 3, "approved_ratio_pct": 75.0},
            {"legal_name": f"{marker}-low", "total_jobs": 12, "approved": 3, "rejected": 9, "approved_ratio_pct": 25.0},
        ],
    )

    response = client.get("/internal/audit/stats/company")
    assert response.status_code == 200
    payload = response.json()

    assert payload["min_total_jobs"] == 10
    items = payload["items"]
    assert len(items) == 2
    # Teraz wyniki są sortowane po ilości zaakceptowanych (approved) ofert malejąco
    assert [item["legal_name"] for item in items] == [f"{marker}-high", f"{marker}-low"]

    assert items[0]["total_jobs"] == 12
    assert items[0]["approved"] == 9
    assert items[0]["rejected"] == 3
    assert items[0]["approved_ratio_pct"] == 75.0

    assert items[1]["total_jobs"] == 12
    assert items[1]["approved"] == 3
    assert items[1]["rejected"] == 9
    assert items[1]["approved_ratio_pct"] == 25.0


def test_internal_audit_source_stats_7d(monkeypatch):
    monkeypatch.setattr(
        audit_api,
        "get_audit_source_compliance_stats_last_7d",
        lambda: [
            {"source": "greenhouse:acme", "total_jobs": 2, "approved": 2, "rejected": 0, "approved_ratio_pct": 100.0},
            {"source": "ashby:test", "total_jobs": 4, "approved": 1, "rejected": 3, "approved_ratio_pct": 25.0},
        ],
    )

    response = client.get("/internal/audit/stats/source-7d")
    assert response.status_code == 200
    payload = response.json()

    assert payload["window"] == "last_7_days"
    items = payload["items"]
    # Teraz wyniki są sortowane po ilości zaakceptowanych ofert malejąco
    assert [item["source"] for item in items] == ["greenhouse:acme", "ashby:test"]

    assert items[0]["total_jobs"] == 2
    assert items[0]["approved"] == 2
    assert items[0]["rejected"] == 0
    assert items[0]["approved_ratio_pct"] == 100.0

    assert items[1]["total_jobs"] == 4
    assert items[1]["approved"] == 1
    assert items[1]["rejected"] == 3
    assert items[1]["approved_ratio_pct"] == 25.0


def test_internal_discovery_audit_returns_recent_discovered_ats(monkeypatch):
    marker = "audit-discovery-20260313"
    monkeypatch.setattr(
        discovery_api,
        "get_discovered_company_ats",
        lambda q=None, limit=100: [
            {
                "company_name": f"{marker}-two",
                "provider": "lever",
                "ats_slug": f"{marker}-lever",
                "careers_url": f"https://{marker}-two.example.com/careers",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "company_name": f"{marker}-one",
                "provider": "greenhouse",
                "ats_slug": f"{marker}-greenhouse",
                "careers_url": f"https://{marker}-one.example.com/careers",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            },
        ],
    )

    response = client.get("/internal/discovery/audit")
    assert response.status_code == 200
    payload = response.json()

    assert "count" in payload
    assert "results" in payload
    assert payload["count"] == 2

    marker_results = [item for item in payload["results"] if str(item.get("company_name", "")).startswith(marker)]
    assert len(marker_results) == 2

    assert marker_results[0]["company_name"] == f"{marker}-two"
    assert marker_results[0]["provider"] == "lever"
    assert marker_results[0]["ats_slug"] == f"{marker}-lever"
    assert marker_results[0]["careers_url"] == f"https://{marker}-two.example.com/careers"
    assert marker_results[0]["created_at"] >= marker_results[1]["created_at"]

    assert marker_results[1]["company_name"] == f"{marker}-one"
    assert marker_results[1]["provider"] == "greenhouse"
    assert marker_results[1]["ats_slug"] == f"{marker}-greenhouse"
    assert marker_results[1]["careers_url"] == f"https://{marker}-one.example.com/careers"

    assert len(payload["results"]) <= 100


def test_internal_discovery_candidates_returns_companies_without_ats(monkeypatch):
    marker = "discovery-candidates-20260313"
    monkeypatch.setattr(
        discovery_api,
        "get_discovery_candidates",
        lambda q=None, limit=50: [
            {
                "legal_name": f"{marker}-null-checked",
                "careers_last_checked_at": None,
                "ats_guess_last_checked_at": None,
            },
            {
                "legal_name": f"{marker}-old-checked",
                "careers_last_checked_at": datetime.now(timezone.utc).isoformat(),
                "ats_guess_last_checked_at": datetime.now(timezone.utc).isoformat(),
            },
        ],
    )

    response = client.get("/internal/discovery/candidates")
    assert response.status_code == 200
    payload = response.json()

    assert "count" in payload
    assert "results" in payload
    assert payload["count"] == len(payload["results"])
    assert len(payload["results"]) <= 50

    marker_results = [row for row in payload["results"] if str(row.get("legal_name", "")).startswith(marker)]
    assert len(marker_results) == 2

    assert marker_results[0]["legal_name"] == f"{marker}-null-checked"
    assert marker_results[0]["careers_last_checked_at"] is None
    assert marker_results[0]["ats_guess_last_checked_at"] is None
    assert marker_results[1]["legal_name"] == f"{marker}-old-checked"
    assert marker_results[1]["careers_last_checked_at"] is not None
    assert marker_results[1]["ats_guess_last_checked_at"] is not None


def test_internal_discovery_run_returns_metrics(monkeypatch):
    fake_result = {
        "status": "ok",
        "actions": ["discovery_completed"],
        "metrics": {
            "pipeline": "discovery",
            "careers": {"checked": 10, "queued": 4},
            "ats_guessing": {"detected": 3},
        },
    }

    monkeypatch.setattr(discovery_api, "run_discovery_pipeline", lambda: fake_result)

    response = client.post("/internal/discovery/run")
    assert response.status_code == 200
    payload = response.json()

    assert payload.get("status") == "ok"
    assert payload.get("metrics", {})["pipeline"] == "discovery"
    assert payload.get("metrics", {})["careers"]["checked"] == 10
    assert payload.get("metrics", {})["ats_guessing"]["detected"] == 3
