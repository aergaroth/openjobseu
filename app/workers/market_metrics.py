import logging
import time
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

logger = logging.getLogger("openjobseu.worker.market_metrics")

def run_market_metrics_worker() -> dict:
    start_time = time.perf_counter()
    today = datetime.now(timezone.utc).date()
    db_engine = get_engine()

    try:
        with db_engine.begin() as conn:
            stats = compute_market_stats(conn, today)
            insert_market_daily_stats(conn, stats)

            segment_rows = compute_market_segments(conn, today)
            insert_market_segments(conn, segment_rows)
            
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        metrics = {
            "component": "market_metrics",
            "status": "ok",
            "date": today.isoformat(),
            "jobs_created": stats["jobs_created"],
            "jobs_expired": stats["jobs_expired"],
            "jobs_active": stats["jobs_active"],
            "jobs_reposted": stats["jobs_reposted"],
            "segments_count": len(segment_rows),
            "duration_ms": duration_ms,
        }
        logger.info("market_metrics_completed", extra=metrics)
        return {"actions": ["market_metrics_updated"], "metrics": metrics}
        
    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error("market_metrics_failed", extra={"error": str(e), "duration_ms": duration_ms})
        return {"actions": [], "metrics": {"component": "market_metrics", "status": "error", "error": str(e), "duration_ms": duration_ms}}