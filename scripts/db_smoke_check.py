# scripts/db_smoke_check.py
import requests
from collections import Counter

BASE_URL = "http://127.0.0.1:8000"
DB_PATH = "data/openjobseu.db"


def http_check():
    print("→ health check")
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    r.raise_for_status()
    print("  OK")


def run_tick():
    print("→ running tick")
    r = requests.post(f"{BASE_URL}/internal/tick", timeout=30)
    r.raise_for_status()
    payload = r.json()
    print("  actions:", payload.get("actions"))
    return payload


def db_check():
    print("→ db inspection")
    from sqlalchemy import text
    from app.db import get_engine

    engine = get_engine()

    with engine.connect() as conn:
        total_row = conn.execute(text("SELECT COUNT(*) AS cnt FROM jobs")).fetchone()
        total = total_row[0] if total_row is not None else 0

        ids_rows = conn.execute(text("SELECT job_id FROM jobs")).mappings().all()
        ids = [r["job_id"] for r in ids_rows]

        status_rows = conn.execute(text("SELECT status, COUNT(*) AS cnt FROM jobs GROUP BY status")).mappings().all()
        statuses = {r["status"]: r["cnt"] for r in status_rows}

    print(f"  jobs total: {total}")
    print(f"  unique job_ids: {len(set(ids))}")
    print(f"  status breakdown: {statuses}")

    assert total == len(set(ids)), "DUPLICATE job_id DETECTED"


def feed_check():
    print("→ feed check")
    r = requests.get(f"{BASE_URL}/jobs/feed", timeout=10)
    r.raise_for_status()
    data = r.json()
    if len(data) == 0:
        print("  NOTE: feed empty – jobs may still be in NEW state")

    return len(data)


if __name__ == "__main__":
    http_check()
    tick_result = run_tick()
    db_check()
    feed_count = feed_check()

    print("\n✓ DB smoke check finished OK")
