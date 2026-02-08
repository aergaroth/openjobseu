from datetime import datetime, timezone

from ingestion.adapters.remoteok_api import RemoteOkApiAdapter
from app.workers.normalization.remoteok import normalize_remoteok_job
from app.workers.ingestion.logging import log_ingestion
from storage.sqlite import init_db, upsert_job

SOURCE = "remoteok"


def run_remoteok_ingestion() -> dict:
    log_ingestion(source=SOURCE, phase="start")

    init_db()
    persisted = 0

    try:
        adapter = RemoteOkApiAdapter()
        entries = adapter.fetch()

        log_ingestion(
            source=SOURCE,
            phase="fetch",
            raw_count=len(entries),
        )

        for raw in entries:
            job = normalize_remoteok_job(raw)
            if not job:
                continue

            upsert_job(job)
            persisted += 1

        log_ingestion(
            source=SOURCE,
            phase="end",
            persisted=persisted,
        )

        return {
            "actions": [f"{SOURCE}_ingested:{persisted}"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        log_ingestion(
            source=SOURCE,
            phase="error",
            error=str(exc),
        )
        raise
