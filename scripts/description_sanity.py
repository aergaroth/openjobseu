#!/usr/bin/env python3
"""
Audits and optionally cleans up job descriptions in the database using
predefined spam or garbage patterns (e.g., leftover tracking markers).
"""

import argparse
import os
import sys

# Zapewnienie dostępu do modułów projektu
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text
from storage.db_engine import get_engine
from app.domain.jobs.cleaning import SPAM_PATTERNS, clean_html

engine = get_engine()


def clean_description_text(description: str) -> tuple[str, list[str]]:
    """Zwraca wyczyszczony opis oraz listę zaaplikowanych napraw."""
    if not description:
        return "", []

    cleaned = description
    applied_fixes = []

    # 1. Czyszczenie HTML do Markdown (nowy, ulepszony silnik)
    new_cleaned = clean_html(cleaned)
    if new_cleaned != cleaned:
        cleaned = new_cleaned
        applied_fixes.append("html_to_markdown")

    # 2. Usuwanie specyficznego spamu (np. tracking pixeli)
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
            suspicious.append(
                {
                    "job_id": row["job_id"],
                    "source": row["source"],
                    "reasons": fixes,
                    "old_length": len(orig_desc),
                    "new_length": len(cleaned_desc),
                    "cleaned_description": cleaned_desc,
                }
            )

    return suspicious


def apply_safe_fixes(conn, suspicious_rows: list[dict]) -> int:
    if not suspicious_rows:
        return 0

    # Przygotowanie danych do zbiorczego update'u (Bulk Update)
    update_data = [{"desc": row["cleaned_description"], "job_id": row["job_id"]} for row in suspicious_rows]

    # Wykonanie wszystkich zmian w jednym zapytaniu do bazy (executemany)
    conn.execute(text("UPDATE jobs SET description = :desc WHERE job_id = :job_id"), update_data)
    return len(update_data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanity-check and optionally repair spam/garbage in descriptions.")
    parser.add_argument("--source", type=str, help="Filter by specific source (e.g. remoteok)")
    parser.add_argument("--fix", action="store_true", help="Apply safe automatic fixes.")
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="How many suspicious rows to print (default: 25).",
    )
    args = parser.parse_args()

    with engine.connect() as conn:
        suspicious = find_suspicious_rows(conn, args.source)
        print(f"suspicious_rows={len(suspicious)}")

        for row in suspicious[: max(args.limit, 0)]:
            print(
                f"[{row['source']}] {row['job_id']} | fixes: {', '.join(row['reasons'])} | lengths: {row['old_length']} -> {row['new_length']}"
            )

        if args.fix and suspicious:
            with engine.begin() as begin_conn:
                fixed = apply_safe_fixes(begin_conn, suspicious)
            print(f"fixed_rows={fixed}")
        else:
            print("\nOpcja dry_run_only=1 (uruchom z flagą --fix aby zastosować zmiany do bazy)")


if __name__ == "__main__":
    raise SystemExit(main())
