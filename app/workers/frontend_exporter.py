import base64
import hashlib
import json
import logging
import mimetypes
import os
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger("openjobseu.runtime")

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"
FRONTEND_EXCLUDE_PATTERNS = [
    "node_modules/",
    "tests/",
    "package.json",
    "package-lock.json",
    "playwright.config.ts",
]
_DEFAULT_ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
_DEFAULT_HTML_CACHE_CONTROL = "public, max-age=300"
_DEFAULT_FEED_CACHE_CONTROL = "public, max-age=300"


def _json_serial(obj):
    """Wsparcie serializacji obiektów nienatywnych (np. datetime) dla json.dumps()"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat().replace("+00:00", "Z")
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def _asset_query_suffix(asset_version: str | None) -> str:
    if not asset_version:
        return ""
    return f"?v={quote(asset_version, safe='')}"


def _render_asset_file(file_path: Path, *, asset_version: str | None = None) -> bytes:
    data = file_path.read_bytes()
    if file_path.name != "index.html" or not asset_version:
        return data

    suffix = _asset_query_suffix(asset_version)
    rendered = data.decode("utf-8")
    rendered = rendered.replace("./style.css", f"./style.css{suffix}")
    rendered = rendered.replace("./feed.js", f"./feed.js{suffix}")
    return rendered.encode("utf-8")


def _asset_cache_control(blob_name: str) -> str:
    if blob_name.endswith(".html"):
        return _DEFAULT_HTML_CACHE_CONTROL
    return _DEFAULT_ASSET_CACHE_CONTROL


def _upload_frontend_assets(bucket, *, asset_version: str | None = None) -> int:
    uploaded_files = 0

    if not FRONTEND_DIR.exists() or not FRONTEND_DIR.is_dir():
        return uploaded_files

    for file_path in FRONTEND_DIR.rglob("*"):
        if not file_path.is_file():
            continue

        blob_name = file_path.relative_to(FRONTEND_DIR).as_posix()
        if any(blob_name.startswith(pattern) for pattern in FRONTEND_EXCLUDE_PATTERNS):
            continue

        file_data = _render_asset_file(file_path, asset_version=asset_version)

        local_md5 = base64.b64encode(hashlib.md5(file_data).digest()).decode("utf-8")
        existing_blob = bucket.get_blob(blob_name)
        if existing_blob and existing_blob.md5_hash == local_md5:
            continue

        content_type, _ = mimetypes.guess_type(file_path.name)

        blob = bucket.blob(blob_name)
        blob.cache_control = _asset_cache_control(blob_name)
        blob.upload_from_string(
            file_data,
            content_type=content_type or "application/octet-stream",
        )
        uploaded_files += 1

    return uploaded_files


def _export_feed(bucket) -> tuple[int, int]:
    from collections import Counter
    from storage.repositories.jobs_repository import get_jobs
    from app.api.jobs import (
        serialize_feed_job,
        FEED_LIMIT,
        FEED_VERSION,
        FEED_MIN_COMPLIANCE_SCORE,
    )

    jobs = get_jobs(
        status="visible",
        min_compliance_score=FEED_MIN_COMPLIANCE_SCORE,
        limit=FEED_LIMIT,
        offset=0,
    )

    # Agregaty dla UI
    departments = Counter(job["source_department"] for job in jobs if job.get("source_department"))
    departments_list = [{"name": name, "count": count} for name, count in departments.items()]

    all_salaries_eur = [job["salary_min_eur"] for job in jobs if job.get("salary_min_eur")]
    salary_range_eur = {"min": min(all_salaries_eur), "max": max(all_salaries_eur)} if all_salaries_eur else {}

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc),
            "count": len(jobs),
            "status": "visible",
            "limit": FEED_LIMIT,
            "version": FEED_VERSION,
            "departments": departments_list,
            "salary_range_eur": salary_range_eur,
        },
        "jobs": [serialize_feed_job(job) for job in jobs],
    }

    feed_blob = bucket.blob("feed.json")
    feed_blob.cache_control = _DEFAULT_FEED_CACHE_CONTROL
    feed_blob.upload_from_string(
        json.dumps(payload, ensure_ascii=False, default=_json_serial, separators=(",", ":")),
        content_type="application/json",
    )
    return len(jobs), 1


def run_frontend_export(
    sync_assets: bool = False,
    *,
    asset_version: str | None = None,
    export_feed: bool = True,
) -> dict:
    """
    Pobiera najświeższy, zwalidowany feed ofert z bazy i wgrywa jako statyczny plik JSON
    do publicznego bucketa GCS. Opcjonalnie kopiuje zawartość folderu `frontend`
    (pomijając niezmienione pliki za pomocą weryfikacji MD5) i może dodać prosty
    cache-busting dla `style.css` oraz `feed.js` przez wersjonowany query string w `index.html`.
    """
    bucket_name = os.getenv("PUBLIC_FEED_BUCKET")
    if not bucket_name:
        return {"status": "skipped", "reason": "no_bucket_configured"}

    logger.info(
        "exporting_frontend_to_gcs",
        extra={
            "bucket": bucket_name,
            "sync_assets": sync_assets,
            "export_feed": export_feed,
            "asset_version": asset_version,
        },
    )

    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        uploaded_files = 0
        exported_jobs = 0

        if sync_assets:
            uploaded_files += _upload_frontend_assets(bucket, asset_version=asset_version)

        if export_feed:
            exported_jobs, feed_uploads = _export_feed(bucket)
            uploaded_files += feed_uploads

        logger.info(
            "frontend_exported_to_gcs",
            extra={
                "job_count": exported_jobs,
                "uploaded_files": uploaded_files,
                "sync_assets": sync_assets,
                "export_feed": export_feed,
                "asset_version": asset_version,
            },
        )
        return {
            "status": "ok",
            "exported_jobs": exported_jobs,
            "uploaded_files": uploaded_files,
            "synced_assets": sync_assets,
            "exported_feed": export_feed,
            "asset_version": asset_version,
        }

    except Exception as e:
        logger.exception("frontend_export_failed", extra={"error": str(e)})
        return {"status": "error", "error": str(e)}
