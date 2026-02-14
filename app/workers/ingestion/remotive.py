from datetime import datetime, timezone
from time import perf_counter

from ingestion.adapters.remotive_api import RemotiveApiAdapter
from app.workers.normalization.remotive import normalize_remotive_job
from app.workers.ingestion.log_helpers import log_ingestion
from app.workers.policy.enforcement import apply_policy_v1
from storage.sqlite import init_db, upsert_job

SOURCE = "remotive"


def run_remotive_ingestion() -> dict:
    log_ingestion(source=SOURCE, phase="start")

    init_db()
    started = perf_counter()
    actions = []
    raw_count = 0
    persisted = 0
    skipped = 0

    try:
        adapter = RemotiveApiAdapter()

        entries = adapter.fetch()
        raw_count = len(entries)
        log_ingestion(
            source=SOURCE,
            phase="fetch",
            raw_count=raw_count,
        )

        for raw in entries:
            job = normalize_remotive_job(raw)
            job = apply_policy_v1(job, source=SOURCE)
            if not job:
                skipped += 1
                continue

            upsert_job(job)
            persisted += 1

        actions.append(f"{SOURCE}_ingested:{persisted}")
        duration_ms = int((perf_counter() - started) * 1000)

        log_ingestion(
            source=SOURCE,
            phase="end",
            raw_count=raw_count,
            persisted=persisted,
            skipped=skipped,
            duration_ms=duration_ms,
        )

    except Exception as exc:
        actions.append(f"{SOURCE}_failed")
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

    return {
        "actions": actions,
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
