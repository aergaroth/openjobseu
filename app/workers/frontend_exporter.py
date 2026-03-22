import json
import logging
import mimetypes
import os
from datetime import date, datetime, timezone
from pathlib import Path

from storage.repositories.jobs_repository import get_jobs
from app.api.jobs import (
    serialize_feed_job,
    FEED_LIMIT,
    FEED_VERSION,
    FEED_MIN_COMPLIANCE_SCORE,
)

logger = logging.getLogger("openjobseu.runtime")

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"


def _json_serial(obj):
    """Wsparcie serializacji obiektów nienatywnych (np. datetime) dla json.dumps()"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat().replace("+00:00", "Z")
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def run_frontend_export() -> dict:
    """
    Pobiera najświeższy, zwalidowany feed ofert z bazy i wgrywa jako statyczny plik JSON
    do publicznego bucketa GCS. Kopiuje również całą zawartość folderu 'frontend'.
    """
    bucket_name = os.getenv("PUBLIC_FEED_BUCKET")
    if not bucket_name:
        return {"status": "skipped", "reason": "no_bucket_configured"}

    logger.info("exporting_frontend_to_gcs", extra={"bucket": bucket_name})

    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        uploaded_files = 0

        # 1. Kopiowanie plików statycznych z folderu frontend
        if FRONTEND_DIR.exists() and FRONTEND_DIR.is_dir():
            for file_path in FRONTEND_DIR.rglob("*"):
                if file_path.is_file():
                    blob_name = file_path.relative_to(FRONTEND_DIR).as_posix()
                    content_type, _ = mimetypes.guess_type(file_path.name)

                    blob = bucket.blob(blob_name)
                    blob.cache_control = "public, max-age=3600"  # Dłuższy cache dla assetów z racji ew. CDN
                    blob.upload_from_filename(
                        str(file_path),
                        content_type=content_type or "application/octet-stream",
                    )
                    uploaded_files += 1

        # 2. Generowanie pliku feed.json z najnowszymi ofertami
        jobs = get_jobs(
            status="visible",
            min_compliance_score=FEED_MIN_COMPLIANCE_SCORE,
            limit=FEED_LIMIT,
            offset=0,
        )

        payload = {
            "meta": {
                "generated_at": datetime.now(timezone.utc),
                "count": len(jobs),
                "status": "visible",
                "limit": FEED_LIMIT,
                "version": FEED_VERSION,
            },
            "jobs": [serialize_feed_job(job) for job in jobs],
        }

        feed_blob = bucket.blob("feed.json")
        feed_blob.cache_control = "public, max-age=300"
        feed_blob.upload_from_string(
            json.dumps(payload, ensure_ascii=False, default=_json_serial, separators=(",", ":")),
            content_type="application/json",
        )
        uploaded_files += 1

        logger.info(
            "frontend_exported_to_gcs",
            extra={"job_count": len(jobs), "uploaded_files": uploaded_files},
        )
        return {
            "status": "ok",
            "exported_jobs": len(jobs),
            "uploaded_files": uploaded_files,
        }

    except Exception as e:
        logger.exception("frontend_export_failed", extra={"error": str(e)})
        return {"status": "error", "error": str(e)}
