#!/usr/bin/env python3

import argparse
from pathlib import Path
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.workers.normalization.weworkremotely import _safe_wwr_source_job_id
from sqlalchemy import text
from storage.db_engine import get_engine

engine = get_engine()



def migrate(conn, apply: bool) -> tuple[int, int]:
    rows = conn.execute(
        text("""
            SELECT job_id, source_job_id, source_url
            FROM jobs
            WHERE source = 'weworkremotely'
        """),
    ).mappings().all()

    updates = []
    skipped_collisions = 0

    existing_ids = {
        r[0]
        for r in conn.execute(text("SELECT job_id FROM jobs")).fetchall()
    }

    for row in rows:
        old_job_id = row["job_id"]
        source_url = (row["source_url"] or "").strip()
        old_source_job_id = (row["source_job_id"] or "").strip()
        if not source_url:
            continue

        new_source_job_id = _safe_wwr_source_job_id(old_source_job_id, source_url)
        new_job_id = f"weworkremotely:{new_source_job_id}"

        if new_job_id == old_job_id and new_source_job_id == old_source_job_id:
            continue

        if new_job_id != old_job_id and new_job_id in existing_ids:
            skipped_collisions += 1
            print(f"skip_collision old={old_job_id} new={new_job_id}")
            continue

        updates.append((new_job_id, new_source_job_id, old_job_id))

    if apply and updates:
        payloads = [
            {"job_id": new, "source_job_id": src, "old_job_id": old}
            for new, src, old in updates
        ]
        with engine.begin() as begin_conn:
            begin_conn.execute(
                text("""
                    UPDATE jobs
                    SET
                        job_id = :job_id,
                        source_job_id = :source_job_id
                    WHERE job_id = :old_job_id
                """),
                payloads,
            )

    return len(updates), skipped_collisions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate WeWorkRemotely IDs to URL-safe source_job_id/job_id.",
    )
    parser.add_argument(
        "--db-path",
        default="data/openjobseu.db",
        help="Path to SQLite database (default: data/openjobseu.db).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag script runs in dry-run mode.",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 2

        with engine.connect() as conn:
            planned, skipped = migrate(conn, apply=args.apply)
            mode = "apply" if args.apply else "dry_run"
            print(f"mode={mode} planned_updates={planned} skipped_collisions={skipped}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
