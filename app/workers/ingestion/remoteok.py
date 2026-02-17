from datetime import datetime, timezone
from time import perf_counter

from ingestion.adapters.remoteok_api import RemoteOkApiAdapter
from app.workers.normalization.remoteok import normalize_remoteok_job
from app.workers.ingestion.log_helpers import log_ingestion
from app.workers.policy.enforcement import apply_policy_v1
from storage.sqlite import init_db, upsert_job

SOURCE = "remoteok"


def run_remoteok_ingestion() -> dict:
    # init_db()  # initialized at app startup in app/main.py
    started = perf_counter()
    fetched_count = 0
    normalized_count = 0
    accepted_count = 0
    rejected_policy_count = 0
    rejected_by_reason = {
        "non_remote": 0,
        "geo_restriction": 0,
    }
    remote_model_counts = {
        "remote_only": 0,
        "remote_but_geo_restricted": 0,
        "non_remote": 0,
        "unknown": 0,
    }
    skipped = 0

    try:
        adapter = RemoteOkApiAdapter()
        entries = adapter.fetch()
        fetched_count = len(entries)

        log_ingestion(
            source=SOURCE,
            phase="fetch",
            raw_count=fetched_count,
        )

        for raw in entries:
            normalized_job = normalize_remoteok_job(raw)
            if not normalized_job:
                skipped += 1
                continue
            normalized_count += 1

            job, reason = apply_policy_v1(normalized_job, source=SOURCE)
            model = normalized_job.get("_compliance", {}).get("remote_model", "unknown")
            if model not in remote_model_counts:
                model = "unknown"
            remote_model_counts[model] += 1
            if not job:
                rejected_policy_count += 1
                if reason in rejected_by_reason:
                    rejected_by_reason[reason] += 1
                skipped += 1
                continue

            upsert_job(job)
            accepted_count += 1

        duration_ms = int((perf_counter() - started) * 1000)
        log_ingestion(
            source=SOURCE,
            phase="ingestion_summary",
            fetched=fetched_count,
            normalized=normalized_count,
            accepted=accepted_count,
            rejected_policy=rejected_policy_count,
            rejected_non_remote=rejected_by_reason["non_remote"],
            rejected_geo_restriction=rejected_by_reason["geo_restriction"],
            remote_model_counts=remote_model_counts.copy(),
            duration_ms=duration_ms,
        )

        return {
            "actions": [f"{SOURCE}_ingested:{accepted_count}"],
            "metrics": {
                "source": SOURCE,
                "status": "ok",
                "fetched_count": fetched_count,
                "normalized_count": normalized_count,
                "accepted_count": accepted_count,
                "rejected_policy_count": rejected_policy_count,
                "policy_rejected_total": rejected_policy_count,
                "policy_rejected_by_reason": rejected_by_reason.copy(),
                "remote_model_counts": remote_model_counts.copy(),
                "raw_count": fetched_count,
                "persisted_count": accepted_count,
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
            raw_count=fetched_count,
            persisted=accepted_count,
            skipped=skipped,
            normalized=normalized_count,
            rejected_policy=rejected_policy_count,
            rejected_non_remote=rejected_by_reason["non_remote"],
            rejected_geo_restriction=rejected_by_reason["geo_restriction"],
            duration_ms=duration_ms,
            error=str(exc),
        )
        raise
