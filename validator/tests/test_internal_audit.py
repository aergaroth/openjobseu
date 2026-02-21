from fastapi.testclient import TestClient

import app.internal as internal_api
from app.main import app
from storage.sqlite import get_conn, init_db, upsert_job

client = TestClient(app)


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
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET
                compliance_status = ?,
                compliance_score = ?,
                remote_class = ?,
                geo_class = ?
            WHERE job_id = ?
            """,
            (
                compliance_status,
                int(compliance_score),
                remote_class,
                geo_class,
                job_id,
            ),
        )
        conn.commit()


def test_internal_audit_page_renders_html():
    response = client.get("/internal/audit")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/html")
    assert "Offer Audit Panel" in response.text


def test_internal_audit_jobs_filters_and_counts():
    init_db()

    job_1 = _make_job(
        "audit:1",
        source="remotive",
        status="new",
        company="Acme",
        title="Backend Engineer",
        remote_scope="EU-wide",
    )
    job_2 = _make_job(
        "audit:2",
        source="remotive",
        status="active",
        company="Beta",
        title="Frontend Engineer",
        remote_scope="Poland",
    )
    job_3 = _make_job(
        "audit:3",
        source="remoteok",
        status="new",
        company="Acme Corp",
        title="Data Engineer",
        remote_scope="USA only",
    )

    upsert_job(job_1)
    upsert_job(job_2)
    upsert_job(job_3)

    _set_compliance(
        job_1["job_id"],
        compliance_status="approved",
        compliance_score=95,
        remote_class="remote_only",
        geo_class="eu_region",
    )
    _set_compliance(
        job_2["job_id"],
        compliance_status="review",
        compliance_score=60,
        remote_class="unknown",
        geo_class="eu_member_state",
    )
    _set_compliance(
        job_3["job_id"],
        compliance_status="rejected",
        compliance_score=0,
        remote_class="non_remote",
        geo_class="non_eu",
    )

    response = client.get(
        "/internal/audit/jobs",
        params={
            "source": "remotive",
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
    assert data["counts"]["compliance_status"]["approved"] == 1
    assert data["counts"]["compliance_status"]["review"] == 1

    response_filtered = client.get(
        "/internal/audit/jobs",
        params={
            "company": "acme",
            "min_compliance_score": 80,
        },
    )
    assert response_filtered.status_code == 200
    filtered = response_filtered.json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["job_id"] == "audit:1"


def test_internal_audit_tick_dev_runs_script(monkeypatch):
    captured = {}

    class FakeResult:
        returncode = 0
        stdout = "tick done"
        stderr = ""

    def fake_run(cmd, cwd, capture_output, text, timeout, check):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["timeout"] = timeout
        captured["check"] = check
        return FakeResult()

    monkeypatch.setattr(internal_api.subprocess, "run", fake_run)

    response = client.post("/internal/audit/tick-dev")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["returncode"] == 0
    assert payload["stdout"] == "tick done"
    assert payload["stderr"] == ""

    assert captured["cmd"][0] == "bash"
    assert captured["cmd"][1].endswith("scripts/tick-dev.sh")
    assert captured["capture_output"] is True
    assert captured["text"] is True
