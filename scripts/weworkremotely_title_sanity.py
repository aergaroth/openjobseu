#!/usr/bin/env python3

import argparse
import sqlite3
from pathlib import Path


def looks_like_url_fragment(value: str) -> bool:
    v = (value or "").strip().lower()
    return (
        v.startswith("http")
        or v.startswith("www.")
        or "://" in v
        or "/" in v
        or v.endswith(".com")
        or v.endswith(".org")
        or v.endswith(".io")
    )


def title_looks_like_url(value: str) -> bool:
    v = (value or "").strip().lower()
    return (
        v.startswith("http://")
        or v.startswith("https://")
        or v.startswith("www.")
        or "://" in v
    )


def split_url_prefixed_title(title: str) -> tuple[str, str] | None:
    """
    Return (prefix, clean_title) for pattern:
    "<url-like-prefix>: <title>"
    """
    raw = (title or "").strip()
    if ":" not in raw:
        return None

    prefix, suffix = raw.split(":", 1)
    prefix = prefix.strip()
    suffix = suffix.strip()

    if not prefix or not suffix:
        return None

    if not looks_like_url_fragment(prefix):
        return None

    if looks_like_url_fragment(suffix):
        return None

    return prefix, suffix


def find_suspicious_wwr_rows(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT
            job_id,
            title,
            source_url
        FROM jobs
        WHERE source = 'weworkremotely'
        """
    ).fetchall()

    suspicious = []
    for row in rows:
        title = (row["title"] or "").strip()
        source_url = (row["source_url"] or "").strip()

        reasons = []
        if title and title_looks_like_url(title):
            reasons.append("title_looks_like_url")
        if title and source_url and title == source_url:
            reasons.append("title_equals_source_url")
        if split_url_prefixed_title(title):
            reasons.append("url_prefix_before_title")

        if reasons:
            suspicious.append(
                {
                    "job_id": row["job_id"],
                    "title": row["title"],
                    "source_url": row["source_url"],
                    "reasons": reasons,
                }
            )

    return suspicious


def apply_safe_fixes(conn: sqlite3.Connection, suspicious_rows: list[dict]) -> int:
    fixed = 0

    for row in suspicious_rows:
        parsed = split_url_prefixed_title(row["title"] or "")
        if not parsed:
            continue

        _prefix, clean_title = parsed
        conn.execute(
            """
            UPDATE jobs
            SET title = ?
            WHERE job_id = ?
            """,
            (clean_title, row["job_id"]),
        )
        fixed += 1

    if fixed:
        conn.commit()

    return fixed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sanity-check and optional repair of WeWorkRemotely titles.",
    )
    parser.add_argument(
        "--db-path",
        default="data/openjobseu.db",
        help="Path to SQLite database (default: data/openjobseu.db)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe automatic fixes (URL-prefix title pattern only).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="How many suspicious rows to print (default: 25).",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 2

    conn = sqlite3.connect(str(db_path))

    try:
        suspicious = find_suspicious_wwr_rows(conn)
        print(f"suspicious_rows={len(suspicious)}")

        to_print = suspicious[: max(args.limit, 0)]
        for row in to_print:
            print("-" * 80)
            print(f"job_id:      {row['job_id']}")
            print(f"reasons:     {', '.join(row['reasons'])}")
            print(f"title:       {row['title']}")
            print(f"source_url:  {row['source_url']}")

        if args.fix:
            fixed = apply_safe_fixes(conn, suspicious)
            print(f"fixed_rows={fixed}")
        else:
            print("dry_run_only=1 (run with --fix to apply safe fixes)")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
