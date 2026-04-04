import json
import logging
import os
from datetime import datetime, timezone

from storage.repositories.audit_repository import (
    get_audit_company_compliance_stats,
    get_audit_source_compliance_stats_last_7d,
    get_rejection_reasons_by_source,
    get_source_compliance_trend,
)

logger = logging.getLogger("openjobseu.runtime")


def _build_snapshot() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_trend": get_source_compliance_trend(days=30),
        "rejection_reasons": get_rejection_reasons_by_source(days=30),
        "company_stats": get_audit_company_compliance_stats(min_total_jobs=5),
        "source_7d": get_audit_source_compliance_stats_last_7d(),
    }


def run_audit_export() -> dict:
    bucket_name = os.getenv("INTERNAL_AUDIT_BUCKET")
    if not bucket_name:
        return {"status": "skipped", "reason": "no_bucket_configured"}

    logger.info("audit_export_started", extra={"bucket": bucket_name})

    try:
        from google.cloud import storage

        snapshot = _build_snapshot()
        payload = json.dumps(snapshot, default=str)

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob("audit_snapshot.json")
        blob.cache_control = "no-store"
        blob.upload_from_string(payload, content_type="application/json")

    except Exception as e:
        logger.exception("audit_export_failed", extra={"error": str(e)})
        return {"status": "error", "error": str(e)}

    logger.info("audit_export_done", extra={"bucket": bucket_name})
    return {"status": "ok"}
