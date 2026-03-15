from sqlalchemy import text

from storage.db_engine import get_engine
from storage.db_logic import upsert_job

engine = get_engine()


def _make_job(
    job_id: str,
    *,
    source: str,
    source_job_id: str,
    title: str,
    description: str,
) -> dict:
    return {
        "job_id": job_id,
        "source": source,
        "source_job_id": source_job_id,
        "source_url": f"https://example.com/jobs/{job_id}",
        "title": title,
        "company_name": "Acme",
        "description": description,
        "remote_source_flag": True,
        "remote_scope": "Europe",
        "status": "new",
        "first_seen_at": "2026-01-05T10:00:00+00:00",
    }


def test_upsert_merges_same_fingerprint_from_different_sources():

    job_a = _make_job(
        "greenhouse:acme:123",
        source="greenhouse:acme",
        source_job_id="123",
        title="Backend Engineer",
        description="Build APIs for EU clients.",
    )
    job_b = _make_job(
        "remotive:123",
        source="remotive",
        source_job_id="123",
        title="Backend Engineer",
        description="Build APIs for EU clients.",
    )

    with engine.begin() as conn:
        upsert_job(job_a, conn=conn)
        upsert_job(job_b, conn=conn)

        jobs_count = conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar_one()
        assert int(jobs_count) == 1

        rows = conn.execute(
            text("""
                SELECT source, source_job_id, job_id
                FROM job_sources
                ORDER BY source ASC
            """)
        ).mappings().all()

    assert len(rows) == 2
    assert rows[0]["source"] == "greenhouse:acme"
    assert rows[1]["source"] == "remotive"
    assert rows[0]["source_job_id"] == "123"
    assert rows[1]["source_job_id"] == "123"
    assert rows[0]["job_id"] == rows[1]["job_id"]


def test_upsert_reuses_same_source_mapping():

    first = _make_job(
        "remotive:first",
        source="remotive",
        source_job_id="42",
        title="Backend Engineer",
        description="Build APIs for EU clients.",
    )
    updated = _make_job(
        "remotive:second",
        source="remotive",
        source_job_id="42",
        title="Principal Backend Engineer",
        description="Build APIs for EU clients and mentor.",
    )

    with engine.begin() as conn:
        upsert_job(first, conn=conn)
        upsert_job(updated, conn=conn)

        row = conn.execute(
            text("""
                SELECT
                    j.job_id,
                    j.title,
                    js.source,
                    js.source_job_id,
                    js.job_id AS mapped_job_id,
                    js.seen_count
                FROM jobs j
                JOIN job_sources js ON js.job_id = j.job_id
                WHERE js.source = 'remotive' AND js.source_job_id = '42'
            """)
        ).mappings().one()

        jobs_count = conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar_one()
        source_rows_count = conn.execute(text("SELECT COUNT(*) FROM job_sources")).scalar_one()

    assert int(jobs_count) == 1
    assert int(source_rows_count) == 1
    assert row["job_id"] == row["mapped_job_id"]
    assert row["title"] == "Principal Backend Engineer"
    assert int(row["seen_count"]) == 2
