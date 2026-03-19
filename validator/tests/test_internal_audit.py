import os
import uuid
from datetime import datetime, timedelta, timezone
import pytest

# guarantee that the database mode is configured even during module import.
os.environ.setdefault("DB_MODE", "standard")

from fastapi.testclient import TestClient

import app.internal as internal_api
from app.domain.taxonomy.enums import ComplianceStatus, GeoClass, RemoteClass
from app.main import app
from storage.repositories.jobs_repository import upsert_job
from storage.db_engine import get_engine
from sqlalchemy import text

client = TestClient(app)

engine = get_engine()


def _make_job(
    job_id: str,
    *,
    source: str,
    status: str,
    company: str,
    title: str,
    remote_scope: str,
) -> dict:
    return {
        "job_id": job_id,
        "source": source,
        "source_job_id": job_id,
        "source_url": f"https://example.com/jobs/{job_id}",
        "title": title,
        "company_name": company,
        "description": "Role description",
        "remote_source_flag": True,
        "remote_scope": remote_scope,
        "status": status,
        "first_seen_at": "2026-01-05T10:00:00+00:00",
    }


def _set_compliance(
    job_id: str,
    *,
    compliance_status: str,
    compliance_score: int,
    remote_class: str,
    geo_class: str,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE jobs
                SET
                    compliance_status = :compliance_status,
                    compliance_score = :compliance_score,
                    remote_class = :remote_class,
                    geo_class = :geo_class
                WHERE job_id = :job_id
            """),
            {
                "compliance_status": compliance_status,
                "compliance_score": int(compliance_score),
                "remote_class": remote_class,
                "geo_class": geo_class,
                "job_id": job_id,
            },
        )


def _insert_company(legal_name: str) -> str:
    company_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO companies (
                    company_id,
                    legal_name,
                    hq_country,
                    remote_posture,
                    created_at,
                    updated_at
                )
                VALUES (
                    :company_id,
                    :legal_name,
                    'PL',
                    'UNKNOWN',
                    NOW(),
                    NOW()
                )
            """),
            {
                "company_id": company_id,
                "legal_name": legal_name,
            },
        )
    return company_id


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


def test_internal_audit_jobs_filters_and_counts():
    marker = "audit-panel-20260221"

    job_1 = _make_job(
        "audit:1",
        source="greenhouse:alpha",
        status="new",
        company=f"{marker}-alpha",
        title=f"{marker} Backend Engineer",
        remote_scope="EU-wide",
    )
    job_2 = _make_job(
        "audit:2",
        source="greenhouse:alpha",
        status="active",
        company=f"{marker}-beta",
        title=f"{marker} Frontend Engineer",
        remote_scope="Poland",
    )
    job_3 = _make_job(
        "audit:3",
        source="lever:gamma",
        status="new",
        company=f"{marker}-gamma",
        title=f"{marker} Data Engineer",
        remote_scope="USA only",
    )

    with engine.begin() as conn:
        upsert_job(job_1, conn=conn)
        upsert_job(job_2, conn=conn)
        upsert_job(job_3, conn=conn)

    _set_compliance(
        job_1["job_id"],
        compliance_status=ComplianceStatus.APPROVED.value,
        compliance_score=95,
        remote_class=RemoteClass.REMOTE_ONLY.value,
        geo_class=GeoClass.EU_REGION.value,
    )
    _set_compliance(
        job_2["job_id"],
        compliance_status=ComplianceStatus.REVIEW.value,
        compliance_score=60,
        remote_class=RemoteClass.UNKNOWN.value,
        geo_class=GeoClass.EU_MEMBER_STATE.value,
    )
    _set_compliance(
        job_3["job_id"],
        compliance_status=ComplianceStatus.REJECTED.value,
        compliance_score=0,
        remote_class=RemoteClass.NON_REMOTE.value,
        geo_class=GeoClass.NON_EU.value,
    )

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
    assert filtered["total"] == 1
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

    monkeypatch.setattr(internal_api, "tick", fake_tick)

    response = client.post("/internal/audit/tick-dev")
    assert response.status_code == 200
    assert response.text == "tick as text"
    assert captured["force_text"] is True


def test_internal_audit_company_stats():
    marker = "audit-company-stats-20260304"
    company_low = _insert_company(f"{marker}-low")
    company_high = _insert_company(f"{marker}-high")
    company_small = _insert_company(f"{marker}-small")

    updates = []
    with engine.begin() as conn:
        for i in range(12):
            job_id = f"audit-company-low:{i}"
            upsert_job(
                _make_job(
                    job_id,
                    source="greenhouse:low",
                    status="new",
                    company=f"{marker}-low",
                    title=f"{marker} low {i}",
                    remote_scope="Europe",
                ),
                conn=conn,
                company_id=company_low,
            )
            updates.append(
                {
                    "job_id": job_id,
                    "compliance_status": "approved" if i < 3 else "rejected",
                }
            )

        for i in range(12):
            job_id = f"audit-company-high:{i}"
            upsert_job(
                _make_job(
                    job_id,
                    source="greenhouse:high",
                    status="new",
                    company=f"{marker}-high",
                    title=f"{marker} high {i}",
                    remote_scope="Europe",
                ),
                conn=conn,
                company_id=company_high,
            )
            updates.append(
                {
                    "job_id": job_id,
                    "compliance_status": "approved" if i < 9 else "rejected",
                }
            )

        for i in range(10):
            job_id = f"audit-company-small:{i}"
            upsert_job(
                _make_job(
                    job_id,
                    source="greenhouse:small",
                    status="new",
                    company=f"{marker}-small",
                    title=f"{marker} small {i}",
                    remote_scope="Europe",
                ),
                conn=conn,
                company_id=company_small,
            )
            updates.append(
                {
                    "job_id": job_id,
                    "compliance_status": "approved",
                }
            )

        conn.execute(
            text("""
                UPDATE jobs
                SET compliance_status = :compliance_status
                WHERE job_id = :job_id
            """),
            updates,
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


def test_internal_audit_source_stats_7d():
    marker = "audit-source-stats-20260304"
    now = datetime.now(timezone.utc)

    updates = []
    with engine.begin() as conn:
        for i in range(4):
            job_id = f"audit-source-ashby:{i}"
            upsert_job(
                _make_job(
                    job_id,
                    source="ashby:test",
                    status="new",
                    company=f"{marker}-r",
                    title=f"{marker} remotive {i}",
                    remote_scope="Europe",
                ),
                conn=conn,
            )
            updates.append(
                {
                    "job_id": job_id,
                    "compliance_status": "approved" if i == 0 else "rejected",
                    "first_seen_at": now - timedelta(days=2),
                }
            )

        for i in range(2):
            job_id = f"audit-source-greenhouse:{i}"
            upsert_job(
                _make_job(
                    job_id,
                    source="greenhouse:acme",
                    status="new",
                    company=f"{marker}-g",
                    title=f"{marker} greenhouse {i}",
                    remote_scope="Europe",
                ),
                conn=conn,
            )
            updates.append(
                {
                    "job_id": job_id,
                    "compliance_status": "approved",
                    "first_seen_at": now - timedelta(days=3),
                }
            )

        for i in range(2):
            job_id = f"audit-source-old:{i}"
            upsert_job(
                _make_job(
                    job_id,
                    source="workable:old",
                    status="new",
                    company=f"{marker}-o",
                    title=f"{marker} old {i}",
                    remote_scope="Europe",
                ),
                conn=conn,
            )
            updates.append(
                {
                    "job_id": job_id,
                    "compliance_status": "approved",
                    "first_seen_at": now - timedelta(days=10),
                }
            )

        for row in updates:
            conn.execute(
                text("""
                    UPDATE jobs
                    SET
                        compliance_status = :compliance_status,
                        first_seen_at = :first_seen_at
                    WHERE job_id = :job_id
                """),
                {
                    "job_id": row["job_id"],
                    "compliance_status": row["compliance_status"],
                    "first_seen_at": row["first_seen_at"],
                },
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


def test_internal_discovery_audit_returns_recent_discovered_ats():
    marker = "audit-discovery-20260313"
    company_one = _insert_company(f"{marker}-one")
    company_two = _insert_company(f"{marker}-two")

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO company_ats (
                    company_id,
                    provider,
                    ats_slug,
                    careers_url,
                    created_at,
                    updated_at
                )
                VALUES (
                    :company_id,
                    :provider,
                    :ats_slug,
                    :careers_url,
                    :created_at,
                    NOW()
                )
            """),
            [
                {
                    "company_id": company_one,
                    "provider": "greenhouse",
                    "ats_slug": f"{marker}-greenhouse",
                    "careers_url": f"https://{marker}-one.example.com/careers",
                    "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
                },
                {
                    "company_id": company_two,
                    "provider": "lever",
                    "ats_slug": f"{marker}-lever",
                    "careers_url": f"https://{marker}-two.example.com/careers",
                    "created_at": datetime.now(timezone.utc) - timedelta(hours=1),
                },
            ],
        )

    response = client.get("/internal/discovery/audit")
    assert response.status_code == 200
    payload = response.json()

    assert "count" in payload
    assert "results" in payload
    assert payload["count"] >= 2

    marker_results = [
        item
        for item in payload["results"]
        if str(item.get("company_name", "")).startswith(marker)
    ]
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


def test_internal_discovery_candidates_returns_companies_without_ats():
    marker = "discovery-candidates-20260313"
    company_null_checked = _insert_company(f"{marker}-null-checked")
    company_old_checked = _insert_company(f"{marker}-old-checked")
    company_with_ats = _insert_company(f"{marker}-with-ats")
    company_without_careers = _insert_company(f"{marker}-no-careers")

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE companies
                SET
                    careers_url = :careers_url,
                    ats_provider = :ats_provider,
                    careers_last_checked_at = :checked_at,
                    ats_guess_last_checked_at = :checked_at
                WHERE company_id = :company_id
            """),
            [
                {
                    "company_id": company_null_checked,
                    "careers_url": f"https://{marker}-null.example.com/careers",
                    "ats_provider": None,
                    "checked_at": None,
                },
                {
                    "company_id": company_old_checked,
                    "careers_url": f"https://{marker}-old.example.com/careers",
                    "ats_provider": None,
                    "checked_at": datetime.now(timezone.utc) - timedelta(days=1),
                },
                {
                    "company_id": company_with_ats,
                    "careers_url": f"https://{marker}-ats.example.com/careers",
                    "ats_provider": "greenhouse",
                    "checked_at": None,
                },
                {
                    "company_id": company_without_careers,
                    "careers_url": None,
                    "ats_provider": None,
                    "checked_at": None,
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

    marker_results = [
        row
        for row in payload["results"]
        if str(row.get("legal_name", "")).startswith(marker)
    ]
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
        "metrics": {
            "pipeline": "discovery",
            "careers": {"checked": 10, "queued": 4},
            "ats_guessing": {"detected": 3},
        }
    }
    
    monkeypatch.setattr(internal_api, "run_discovery_pipeline", lambda: fake_result)
    
    response = client.post("/internal/discovery/run")
    assert response.status_code == 200
    payload = response.json()
    
    assert payload.get("status") == "ok"
    assert payload.get("metrics", {})["pipeline"] == "discovery"
    assert payload.get("metrics", {})["careers"]["checked"] == 10
    assert payload.get("metrics", {})["ats_guessing"]["detected"] == 3
