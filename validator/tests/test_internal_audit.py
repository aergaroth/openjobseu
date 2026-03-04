import os
import uuid
from datetime import datetime, timedelta, timezone

# guarantee that the database mode is configured even during module import.
os.environ.setdefault("DB_MODE", "standard")

from fastapi.testclient import TestClient

import app.internal as internal_api
from app.domain.classification.enums import ComplianceStatus, GeoClass, RemoteClass
from app.main import app
from storage.db_logic import init_db, upsert_job
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
        "source_job_id": job_id.split(":")[-1],
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
    assert "Offer Audit Panel" in response.text


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
    init_db()
    marker = "audit-panel-20260221"

    job_1 = _make_job(
        "audit:1",
        source="remotive",
        status="new",
        company=f"{marker}-alpha",
        title=f"{marker} Backend Engineer",
        remote_scope="EU-wide",
    )
    job_2 = _make_job(
        "audit:2",
        source="remotive",
        status="active",
        company=f"{marker}-beta",
        title=f"{marker} Frontend Engineer",
        remote_scope="Poland",
    )
    job_3 = _make_job(
        "audit:3",
        source="remoteok",
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
            "source": "remotive",
            "company": marker,
            "limit": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert data["limit"] == 1
    assert len(data["items"]) == 1
    assert data["counts"]["source"]["remotive"] == 2
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
    assert "remotive" in source_values
    assert "remoteok" in source_values


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
    init_db()
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
                    source="remotive",
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
                    source="remotive",
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
                    source="remotive",
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
    assert [item["legal_name"] for item in items] == [f"{marker}-low", f"{marker}-high"]
    assert items[0]["total_jobs"] == 12
    assert items[0]["approved"] == 3
    assert items[0]["rejected"] == 9
    assert items[0]["approved_ratio_pct"] == 25.0
    assert items[1]["approved_ratio_pct"] == 75.0


def test_internal_audit_source_stats_7d():
    init_db()
    marker = "audit-source-stats-20260304"
    now = datetime.now(timezone.utc)

    updates = []
    with engine.begin() as conn:
        for i in range(4):
            job_id = f"audit-source-remotive:{i}"
            upsert_job(
                _make_job(
                    job_id,
                    source="remotive",
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
                    source="remoteok",
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
    assert [item["source"] for item in items] == ["remotive", "greenhouse:acme"]
    assert items[0]["total_jobs"] == 4
    assert items[0]["approved"] == 1
    assert items[0]["rejected"] == 3
    assert items[0]["approved_ratio_pct"] == 25.0
    assert items[1]["approved_ratio_pct"] == 100.0
