from datetime import datetime, timezone

from storage.db_engine import get_engine
from storage.repositories.market_repository import (
    compute_market_stats,
    insert_market_daily_stats,
)
from storage.repositories.market_segments_repository import (
    compute_market_segments,
    insert_market_segments,
)


def run_market_metrics_worker() -> dict:
    today = datetime.now(timezone.utc).date()
    db_engine = get_engine()

    with db_engine.begin() as conn:
        stats = compute_market_stats(conn, today)
        insert_market_daily_stats(conn, stats)

        segment_rows = compute_market_segments(conn, today)
        insert_market_segments(conn, segment_rows)

    return {
        "component": "market_metrics",
        "date": today.isoformat(),
        "jobs_created": stats["jobs_created"],
        "jobs_expired": stats["jobs_expired"],
        "jobs_active": stats["jobs_active"],
        "jobs_reposted": stats["jobs_reposted"],
        "segments_count": len(segment_rows),
    }