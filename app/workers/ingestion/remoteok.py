from datetime import datetime, timezone
from time import perf_counter

from ingestion.adapters.remoteok_api import RemoteOkApiAdapter
from app.workers.normalization.remoteok import normalize_remoteok_job
from app.workers.ingestion.log_helpers import log_ingestion
from storage.sqlite import init_db, upsert_job

SOURCE = "remoteok"


def run_remoteok_ingestion() -> dict:
    log_ingestion(source=SOURCE, phase="start")

    init_db()
    started = perf_counter()
    raw_count = 0
    persisted = 0
    skipped = 0

    try:
        adapter = RemoteOkApiAdapter()
        entries = adapter.fetch()
        raw_count = len(entries)

        log_ingestion(
            source=SOURCE,
            phase="fetch",
            raw_count=raw_count,
        )

        for raw in entries:
            job = normalize_remoteok_job(raw)
            if not job:
                skipped += 1
                continue

            upsert_job(job)
            persisted += 1

        duration_ms = int((perf_counter() - started) * 1000)
        log_ingestion(
            source=SOURCE,
            phase="end",
            raw_count=raw_count,
            persisted=persisted,
            skipped=skipped,
            duration_ms=duration_ms,
        )

        return {
            "actions": [f"{SOURCE}_ingested:{persisted}"],
            "metrics": {
                "source": SOURCE,
                "status": "ok",
                "raw_count": raw_count,
                "persisted_count": persisted,
                "skipped_count": skipped,
                "duration_ms": duration_ms,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        log_ingestion(
            source=SOURCE,
            phase="error",
            raw_count=raw_count,
            persisted=persisted,
            skipped=skipped,
            duration_ms=duration_ms,
            error=str(exc),
        )
        raise
