#!/usr/bin/env python3
"""
One-time backfill: clean HTML descriptions and recompute job_fingerprints atomically.

Addresses jobs ingested before clean_description was applied prior to fingerprint
computation. Handles fingerprint collisions (two records whose clean descriptions
become identical) by merging the duplicate's job_sources into the surviving record
and deleting the duplicate.

DB round-trips:
  1. SELECT  — load all dirty rows (HTML filter applied in Python)
  2. SELECT  — batch collision check via ANY(ARRAY[...])
  3. executemany UPDATE — bulk write in chunks of CHUNK_SIZE

Usage:
    python scripts/backfill_clean_descriptions.py              # dry-run (no changes)
    python scripts/backfill_clean_descriptions.py --fix        # apply changes
    python scripts/backfill_clean_descriptions.py --source greenhouse --fix
"""

import argparse
import logging
import os
import re
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text

from app.domain.jobs.cleaning import clean_description
from app.domain.jobs.identity import compute_job_fingerprint
from storage.db_engine import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_HTML_TAG = re.compile(r"<[a-zA-Z][^>]*>")
CHUNK_SIZE = 500


# ---------------------------------------------------------------------------
# Step 1: load
# ---------------------------------------------------------------------------


def _load_dirty_jobs(conn, source_filter: str | None) -> list[dict]:
    """Single SELECT — Python-side HTML filter keeps only rows that need work."""
    query = """
        SELECT
            job_id,
            source,
            title,
            company_name,
            company_id,
            remote_scope,
            description,
            job_fingerprint
        FROM jobs
    """
    params: dict = {}
    if source_filter:
        query += " WHERE source LIKE :source_pattern"
        params["source_pattern"] = f"{source_filter}%"

    rows = conn.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows if _HTML_TAG.search(r["description"] or "")]


# ---------------------------------------------------------------------------
# Step 2: compute (pure Python, zero DB calls)
# ---------------------------------------------------------------------------


def _compute_cleaned(dirty_jobs: list[dict]) -> list[dict]:
    """
    Returns a list of result dicts with new_desc / new_fp for every dirty job.
    No database access — just CPU.
    """
    results = []
    for job in dirty_jobs:
        provider = (job["source"] or "").split(":")[0]
        new_desc = clean_description(job["description"] or "", source=provider)
        new_fp = compute_job_fingerprint(
            new_desc,
            title=job["title"] or "",
            location=job["remote_scope"],
            company_id=job["company_id"],
            company_name=job["company_name"] or "",
        )
        results.append(
            {
                "job_id": job["job_id"],
                "source": job["source"],
                "old_fp": job["job_fingerprint"],
                "new_desc": new_desc,
                "new_fp": new_fp,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Step 3: detect collisions (one bulk SELECT)
# ---------------------------------------------------------------------------


def _detect_collisions(conn, computed: list[dict]) -> dict[str, str]:
    """
    Returns mapping  new_fp → existing_job_id  for fingerprints that already
    exist in the DB under a *different* job_id (i.e. genuine collisions).
    Uses a single  WHERE job_fingerprint = ANY(ARRAY[...])  query.
    """
    self_ids = {r["job_id"] for r in computed}
    new_fps = list({r["new_fp"] for r in computed})

    if not new_fps:
        return {}

    rows = (
        conn.execute(
            text("SELECT job_id, job_fingerprint FROM jobs WHERE job_fingerprint = ANY(:fps)"),
            {"fps": new_fps},
        )
        .mappings()
        .all()
    )

    return {row["job_fingerprint"]: row["job_id"] for row in rows if row["job_id"] not in self_ids}


# ---------------------------------------------------------------------------
# Step 4: classify + bulk-write
# ---------------------------------------------------------------------------


def _chunked(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def _merge_collision(conn, duplicate_id: str, surviving_id: str, source: str) -> None:
    """Redirect job_sources and delete the duplicate record."""
    logger.info("collision_merge  %s → %s  (%s)", duplicate_id, surviving_id, source)
    conn.execute(
        text("""
            UPDATE job_sources
            SET job_id = :surviving
            WHERE job_id = :dup
              AND NOT EXISTS (
                  SELECT 1 FROM job_sources x
                  WHERE x.job_id        = :surviving
                    AND x.source        = job_sources.source
                    AND x.source_job_id = job_sources.source_job_id
              )
        """),
        {"surviving": surviving_id, "dup": duplicate_id},
    )
    conn.execute(text("DELETE FROM job_sources WHERE job_id = :dup"), {"dup": duplicate_id})
    conn.execute(text("DELETE FROM jobs        WHERE job_id = :dup"), {"dup": duplicate_id})


def _apply(conn, computed: list[dict], collision_map: dict[str, str], dry_run: bool) -> dict:
    stats = {"inspected": len(computed), "updated": 0, "desc_only": 0, "merged": 0}

    updates: list[dict] = []  # description + fingerprint changed, no collision
    desc_only: list[dict] = []  # fingerprint unchanged, only description updated
    collisions: list[dict] = []  # fingerprint collision with existing record

    # --- intra-batch dedup: if two dirty rows produce the same new_fp, the later
    #     one (by iteration order) loses — it merges into the first one we saw.
    seen_new_fps: dict[str, str] = {}  # new_fp → job_id of the first occurrence

    for r in computed:
        new_fp = r["new_fp"]

        if new_fp == r["old_fp"]:
            # Fingerprint window didn't change — update description only
            desc_only.append({"desc": r["new_desc"], "job_id": r["job_id"]})
            continue

        if new_fp in collision_map:
            collisions.append({**r, "surviving_id": collision_map[new_fp]})
            continue

        if new_fp in seen_new_fps:
            # Intra-batch duplicate: two dirty rows clean to the same fingerprint
            collisions.append({**r, "surviving_id": seen_new_fps[new_fp]})
            continue

        seen_new_fps[new_fp] = r["job_id"]
        updates.append({"desc": r["new_desc"], "fp": r["new_fp"], "job_id": r["job_id"]})

    logger.info(
        "classified  full_update=%d  desc_only=%d  collisions=%d",
        len(updates),
        len(desc_only),
        len(collisions),
    )

    if dry_run:
        for r in updates:
            logger.info("  would update  %s", r["job_id"])
        for r in collisions:
            logger.info("  would merge   %s → %s", r["job_id"], r["surviving_id"])
        stats["updated"] = len(updates)
        stats["desc_only"] = len(desc_only)
        stats["merged"] = len(collisions)
        return stats

    # Bulk UPDATE: description + fingerprint (chunked executemany)
    for chunk in _chunked(updates, CHUNK_SIZE):
        conn.execute(
            text("UPDATE jobs SET description = :desc, job_fingerprint = :fp WHERE job_id = :job_id"),
            chunk,
        )
    stats["updated"] = len(updates)

    # Bulk UPDATE: description only (chunked executemany)
    for chunk in _chunked(desc_only, CHUNK_SIZE):
        conn.execute(
            text("UPDATE jobs SET description = :desc WHERE job_id = :job_id"),
            chunk,
        )
    stats["desc_only"] = len(desc_only)

    # Collisions — handled individually (expected to be rare)
    for r in collisions:
        _merge_collision(conn, duplicate_id=r["job_id"], surviving_id=r["surviving_id"], source=r["source"])
    stats["merged"] = len(collisions)

    return stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fix", action="store_true", help="Apply changes (default: dry-run).")
    parser.add_argument("--source", type=str, default=None, help="Filter by source prefix, e.g. 'greenhouse'.")
    args = parser.parse_args()

    dry_run = not args.fix
    if dry_run:
        logger.info("DRY-RUN mode — no changes written (pass --fix to apply)")

    engine = get_engine()

    with engine.connect() as conn:
        dirty = _load_dirty_jobs(conn, source_filter=args.source)

    logger.info("dirty_jobs_found=%d", len(dirty))
    if not dirty:
        logger.info("Nothing to do.")
        return 0

    # Pure-Python step — no DB
    computed = _compute_cleaned(dirty)

    with engine.begin() as conn:
        collision_map = _detect_collisions(conn, computed)
        if collision_map:
            logger.info("collisions_detected=%d", len(collision_map))
        stats = _apply(conn, computed, collision_map, dry_run=dry_run)

    logger.info(
        "done  inspected=%d  updated=%d  desc_only=%d  merged=%d  dry_run=%s",
        stats["inspected"],
        stats["updated"],
        stats["desc_only"],
        stats["merged"],
        dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
