import os
import sys
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import uuid
from datetime import datetime, timezone
from sqlalchemy import text

from storage.db_engine import get_engine

def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


engine = get_engine()


def _chunked(items: list[dict], chunk_size: int):
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


def migrate(*, dry_run: bool, company_batch_size: int, job_batch_size: int):
    now = datetime.now(timezone.utc)

    tx = engine.connect() if dry_run else engine.begin()
    with tx as conn:
        job_names = conn.execute(
            text("""
                SELECT DISTINCT company_name
                FROM jobs
                WHERE company_name IS NOT NULL
                  AND btrim(company_name) <> ''
            """)
        ).scalars().all()
        normalized_job_names = sorted(
            {normalize_name(name) for name in job_names if normalize_name(name)}
        )

        existing = conn.execute(
            text("""
                SELECT company_id, legal_name
                FROM companies
                WHERE legal_name IS NOT NULL
                  AND btrim(legal_name) <> ''
            """)
        ).mappings().all()
        existing_by_normalized_name = {
            normalize_name(str(row["legal_name"])).casefold(): row["company_id"]
            for row in existing
        }

        to_insert: list[dict] = []
        for legal_name in normalized_job_names:
            key = legal_name.casefold()
            if key not in existing_by_normalized_name:
                company_id = uuid.uuid4()
                to_insert.append(
                    {
                        "company_id": company_id,
                        "legal_name": legal_name,
                        "hq_country": "ZZ",
                        "eu_entity_verified": False,
                        "remote_posture": "UNKNOWN",
                        "is_active": False,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                existing_by_normalized_name[key] = company_id

        inserted = len(to_insert)
        if not dry_run and to_insert:
            for batch in _chunked(to_insert, company_batch_size):
                conn.execute(
                    text("""
                        INSERT INTO companies (
                            company_id,
                            legal_name,
                            hq_country,
                            eu_entity_verified,
                            remote_posture,
                            is_active,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            :company_id,
                            :legal_name,
                            :hq_country,
                            :eu_entity_verified,
                            :remote_posture,
                            :is_active,
                            :created_at,
                            :updated_at
                        )
                    """),
                    batch,
                )

        updated = 0
        while True:
            result = conn.execute(
                text("""
                    WITH ranked_companies AS (
                        SELECT
                            company_id,
                            lower(regexp_replace(btrim(legal_name), '\\s+', ' ', 'g')) AS normalized_name,
                            row_number() OVER (
                                PARTITION BY lower(regexp_replace(btrim(legal_name), '\\s+', ' ', 'g'))
                                ORDER BY created_at ASC NULLS LAST, company_id ASC
                            ) AS rn
                        FROM companies
                    ),
                    target_jobs AS (
                        SELECT
                            j.ctid AS job_ctid,
                            rc.company_id
                        FROM jobs j
                        JOIN ranked_companies rc
                          ON rc.rn = 1
                         AND lower(regexp_replace(btrim(j.company_name), '\\s+', ' ', 'g')) = rc.normalized_name
                        WHERE j.company_id IS NULL
                          AND j.company_name IS NOT NULL
                          AND btrim(j.company_name) <> ''
                        LIMIT :limit
                    )
                    UPDATE jobs j
                    SET company_id = t.company_id
                    FROM target_jobs t
                    WHERE j.ctid = t.job_ctid
                """),
                {"limit": job_batch_size},
            )
            updated_batch = result.rowcount or 0
            updated += updated_batch
            if updated_batch < job_batch_size:
                break

        if dry_run:
            conn.rollback()

    print(
        f"Migration complete. dry_run={int(dry_run)} "
        f"normalized_job_names={len(normalized_job_names)} "
        f"to_insert_companies={inserted} backfilled_jobs={updated} "
        f"company_batch_size={company_batch_size} job_batch_size={job_batch_size}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill companies and jobs.company_id.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and execute inside a transaction rollback (no persistent changes).",
    )
    parser.add_argument(
        "--company-batch-size",
        type=int,
        default=1000,
        help="Insert batch size for companies (default: 1000).",
    )
    parser.add_argument(
        "--job-batch-size",
        type=int,
        default=5000,
        help="Update batch size for jobs company_id backfill (default: 5000).",
    )
    args = parser.parse_args()
    if args.company_batch_size < 1:
        parser.error("--company-batch-size must be >= 1")
    if args.job_batch_size < 1:
        parser.error("--job-batch-size must be >= 1")
    return args


if __name__ == "__main__":
    args = parse_args()
    migrate(
        dry_run=args.dry_run,
        company_batch_size=args.company_batch_size,
        job_batch_size=args.job_batch_size,
    )
