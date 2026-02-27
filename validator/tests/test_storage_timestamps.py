from storage.db_logic import init_db, upsert_job
from storage.db_engine import get_engine
from sqlalchemy import text
from datetime import datetime

engine = get_engine()


def _make_job(job_id: str, first_seen_at: str) -> dict:
    return {
        "job_id": job_id,
        "source": "remotive",
        "source_job_id": job_id.split(":")[-1],
        "source_url": f"https://example.com/jobs/{job_id}",
        "title": "Backend Engineer",
        "company_name": "Acme",
        "description": "Role description",
        "remote_source_flag": True,
        "remote_scope": "Europe",
        "status": "new",
        "first_seen_at": first_seen_at,
    }


def test_upsert_uses_source_first_seen_at():
    init_db()

    source_first_seen = "2026-01-05T10:00:00+00:00"
    job = _make_job("remotive:test-first-seen", source_first_seen)
    with engine.begin() as conn:
        upsert_job(job, conn=conn)

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT first_seen_at FROM jobs WHERE job_id = :job_id"),
            {"job_id": job["job_id"]},
        ).fetchone()

    assert row is not None
    v = row[0]
    if isinstance(v, datetime):
        v = v.isoformat()
    else:
        v = str(v)
    assert v == source_first_seen


def test_upsert_keeps_earliest_first_seen_at_on_conflict():
    init_db()

    job_id = "remotive:test-first-seen-conflict"
    older = _make_job(job_id, "2026-01-05T10:00:00+00:00")
    newer = _make_job(job_id, "2026-01-07T10:00:00+00:00")

    with engine.begin() as conn:
        upsert_job(older, conn=conn)
        upsert_job(newer, conn=conn)

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT first_seen_at FROM jobs WHERE job_id = :job_id"),
            {"job_id": job_id},
        ).fetchone()

    assert row is not None
    v = row[0]
    if isinstance(v, datetime):
        v = v.isoformat()
    else:
        v = str(v)
    assert v == older["first_seen_at"]


def test_upsert_persists_derived_compliance_classes():
    init_db()

    job = _make_job("remotive:test-classes", "2026-01-05T10:00:00+00:00")
    job["remote_scope"] = "EU-wide"
    job["_compliance"] = {
        "policy_reason": None,
        "remote_model": "remote_only",
    }

    with engine.begin() as conn:
        upsert_job(job, conn=conn)

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT remote_class, geo_class FROM jobs WHERE job_id = :job_id"),
            {"job_id": job["job_id"]},
        ).fetchone()

    assert row is not None
    assert row[0] == "remote_only"
    assert row[1] == "eu_region"


def test_upsert_marks_geo_non_eu_when_policy_flags_geo_restriction():
    init_db()

    job = _make_job("remotive:test-geo-restriction", "2026-01-05T10:00:00+00:00")
    job["remote_scope"] = "Worldwide"
    job["_compliance"] = {
        "policy_reason": "geo_restriction",
        "remote_model": "remote_but_geo_restricted",
    }

    with engine.begin() as conn:
        upsert_job(job, conn=conn)

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT remote_class, geo_class FROM jobs WHERE job_id = :job_id"),
            {"job_id": job["job_id"]},
        ).fetchone()

    assert row is not None
    assert row[0] == "remote_but_geo_restricted"
    assert row[1] == "non_eu"
