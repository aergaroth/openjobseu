#!/usr/bin/env python3

import argparse
import os
import sys
import re
from pathlib import Path

# Zapewnienie dostępu do modułów projektu
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text
from storage.db_engine import get_engine
from app.utils.cleaning import SPAM_PATTERNS

engine = get_engine()

def clean_description_text(description: str) -> tuple[str, list[str]]:
    """Zwraca wyczyszczony opis oraz listę zaaplikowanych napraw."""
    if not description:
        return "", []

    cleaned = description
    applied_fixes = []

    for name, pattern in SPAM_PATTERNS.items():
        if pattern.search(cleaned):
            cleaned = pattern.sub("", cleaned)
            applied_fixes.append(name)

    return cleaned.strip(), applied_fixes


def find_suspicious_rows(conn, source: str = None) -> list[dict]:
    query = "SELECT job_id, source, description FROM jobs"
    params = {}
    if source:
        query += " WHERE source = :source"
        params["source"] = source
        
    rows = conn.execute(text(query), params).mappings().all()

    suspicious = []
    for row in rows:
        orig_desc = row["description"] or ""
        cleaned_desc, fixes = clean_description_text(orig_desc)
        
        if fixes:
            suspicious.append({
                "job_id": row["job_id"],
                "source": row["source"],
                "reasons": fixes,
                "old_length": len(orig_desc),
                "new_length": len(cleaned_desc),
                "cleaned_description": cleaned_desc,
            })

    return suspicious


def apply_safe_fixes(conn, suspicious_rows: list[dict]) -> int:
    fixed = 0
    for row in suspicious_rows:
        conn.execute(
            text("""
                UPDATE jobs
                SET description = :desc
                WHERE job_id = :job_id
            """),
            {"desc": row["cleaned_description"], "job_id": row["job_id"]},
        )
        fixed += 1
    return fixed


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanity-check and optionally repair spam/garbage in descriptions.")
    parser.add_argument("--source", type=str, help="Filter by specific source (e.g. remoteok)")
    parser.add_argument("--fix", action="store_true", help="Apply safe automatic fixes.")
    parser.add_argument("--limit", type=int, default=25, help="How many suspicious rows to print (default: 25).")
    args = parser.parse_args()

    with engine.connect() as conn:
        suspicious = find_suspicious_rows(conn, args.source)
        print(f"suspicious_rows={len(suspicious)}")

        for row in suspicious[: max(args.limit, 0)]:
            print(f"[{row['source']}] {row['job_id']} | fixes: {', '.join(row['reasons'])} | lengths: {row['old_length']} -> {row['new_length']}")

        if args.fix and suspicious:
            with engine.begin() as begin_conn:
                fixed = apply_safe_fixes(begin_conn, suspicious)
            print(f"fixed_rows={fixed}")
        else:
            print("\nOpcja dry_run_only=1 (uruchom z flagą --fix aby zastosować zmiany do bazy)")

if __name__ == "__main__":
    raise SystemExit(main())