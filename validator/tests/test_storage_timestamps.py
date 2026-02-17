from storage.sqlite import get_conn, init_db, upsert_job


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
    upsert_job(job)

    with get_conn() as conn:
        row = conn.execute(
            "SELECT first_seen_at FROM jobs WHERE job_id = ?",
            (job["job_id"],),
        ).fetchone()

    assert row is not None
    assert row[0] == source_first_seen


def test_upsert_keeps_earliest_first_seen_at_on_conflict():
    init_db()

    job_id = "remotive:test-first-seen-conflict"
    older = _make_job(job_id, "2026-01-05T10:00:00+00:00")
    newer = _make_job(job_id, "2026-01-07T10:00:00+00:00")

    upsert_job(older)
    upsert_job(newer)

    with get_conn() as conn:
        row = conn.execute(
            "SELECT first_seen_at FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == older["first_seen_at"]
