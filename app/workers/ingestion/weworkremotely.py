from datetime import datetime, timezone

from ingestion.adapters.weworkremotely_rss import WeWorkRemotelyRssAdapter
from app.workers.normalization.weworkremotely import (
    normalize_weworkremotely_job,
)
from app.workers.ingestion.log_helpers import log_ingestion
from storage.sqlite import init_db, upsert_job

SOURCE = "weworkremotely"
RSS_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"


def run_weworkremotely_ingestion() -> dict:
    log_ingestion(source=SOURCE, phase="start")

    init_db()
    actions = []
    persisted = 0

    try:
        adapter = WeWorkRemotelyRssAdapter(RSS_URL)

        entries = adapter.fetch()
        log_ingestion(
            source=SOURCE,
            phase="fetch",
            raw_count=len(entries),
        )

        for raw in entries:
            job = normalize_weworkremotely_job(raw)
            if not job:
                continue

            upsert_job(job)
            persisted += 1

        actions.append(f"{SOURCE}_ingested:{persisted}")

        log_ingestion(
            source=SOURCE,
            phase="end",
            persisted=persisted,
        )

    except Exception as exc:
        actions.append(f"{SOURCE}_failed")

        log_ingestion(
            source=SOURCE,
            phase="error",
            error=str(exc),
        )
        raise

    return {
        "actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
