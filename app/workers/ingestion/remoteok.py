from datetime import datetime, timezone

from ingestion.adapters.remoteok_api import RemoteOkApiAdapter
from app.workers.normalization.remoteok import normalize_remoteok_job
from app.workers.ingestion.logging import log_ingestion
from storage.sqlite import init_db, upsert_job

SOURCE = "remoteok"


def run_remoteok_ingestion() -> dict:
    log_ingestion(source=SOURCE, phase="start")

    init_db()
    actions = []
    persisted = 0

    try:
        adapter = RemoteOkApiAdapter()

        log_ingestion(source=SOURCE, phase="fetch")

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
