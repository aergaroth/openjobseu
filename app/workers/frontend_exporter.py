import base64
import hashlib
import json
import logging
import mimetypes
import os
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

from app.workers.chart_generator import (
    generate_line_chart,
    generate_volume_chart,
    svg_to_file,
)
from app.workers.market_types import DailyStats, MarketStatsMeta, MarketStatsResponse
from storage.db_engine import get_engine
from storage.repositories.market_repository import get_active_jobs_compliance_counts, get_market_daily_stats

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
_DEFAULT_MARKET_STATS_CACHE_CONTROL = "public, max-age=300"


def _json_serial(obj):
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


def _build_chart_set(stats: list[DailyStats], days: int) -> dict[str, bytes]:
    """
    Slice stats to the last `days` entries and generate three SVG charts.
    Returns a dict mapping filename suffix → SVG bytes.
    """
    subset = stats[-days:] if stats else []
    dates = [s.date for s in subset]

    volume_svg = generate_volume_chart(
        [s.jobs_created for s in subset],
        [s.jobs_expired for s in subset],
        [s.jobs_active for s in subset],
        dates,
    )
    salary_svg = generate_line_chart(
        [s.avg_salary_eur for s in subset],
        dates,
        "#0D9488",
        lambda v: f"€{int(v):,}/yr",
    )
    remote_svg = generate_line_chart(
        [s.remote_ratio for s in subset],
        dates,
        "#D97706",
        lambda v: f"{int(v * 100)}%",
    )

    return {
        "volume": svg_to_file(volume_svg),
        "salary": svg_to_file(salary_svg),
        "remote": svg_to_file(remote_svg),
    }


def _export_charts(bucket, stats: list[DailyStats]) -> int:
    """
    Upload six SVG chart files (volume/salary/remote × 7d/30d) to GCS.
    Partial failure is logged per file but does not abort remaining uploads.
    Returns count of successfully uploaded files.
    """
    uploaded = 0
    for days in [7, 30]:
        chart_set = _build_chart_set(stats, days)
        for name, svg_bytes in chart_set.items():
            blob_name = f"charts/{name}-{days}d.svg"
            try:
                blob = bucket.blob(blob_name)
                blob.cache_control = _DEFAULT_MARKET_STATS_CACHE_CONTROL
                blob.upload_from_string(svg_bytes, content_type="image/svg+xml")
                uploaded += 1
            except Exception:
                logger.exception("chart_upload_failed", extra={"blob": blob_name})
    return uploaded


def _export_market_stats(bucket, chart_base_url: str) -> tuple[int, int]:
    """
    1. Query market_daily_stats for the last 30 days.
    2. Upload six SVG chart files via _export_charts().
    3. Serialize MarketStatsResponse and upload as market-stats.json.
    Returns (rows_exported, charts_uploaded).
    """
    engine = get_engine()
    with engine.connect() as conn:
        raw_rows = get_market_daily_stats(conn, days=30)
        compliance_counts = get_active_jobs_compliance_counts(conn)

    stats = [DailyStats(**row) for row in raw_rows]
    charts_uploaded = _export_charts(bucket, stats)

    meta = MarketStatsMeta(
        generated_at=datetime.now(timezone.utc).isoformat(),
        days_available=len(stats),
        chart_base_url=chart_base_url,
        **compliance_counts,
    )
    response = MarketStatsResponse(meta=meta, stats=stats)

    stats_blob = bucket.blob("market-stats.json")
    stats_blob.cache_control = _DEFAULT_MARKET_STATS_CACHE_CONTROL
    stats_blob.upload_from_string(
        response.model_dump_json(),
        content_type="application/json",
    )

    return len(stats), charts_uploaded


def run_frontend_export(
    sync_assets: bool = False,
    *,
    asset_version: str | None = None,
    export_feed: bool = True,
    export_market_stats: bool = True,
) -> dict:
    bucket_name = os.getenv("PUBLIC_FEED_BUCKET")
    if not bucket_name:
        return {"status": "skipped", "reason": "no_bucket_configured"}

    chart_base_url = os.getenv("PUBLIC_FEED_BASE_URL", "")

    logger.info(
        "exporting_frontend_to_gcs",
        extra={
            "bucket": bucket_name,
            "sync_assets": sync_assets,
            "export_feed": export_feed,
            "export_market_stats": export_market_stats,
            "asset_version": asset_version,
        },
    )

    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        uploaded_files = 0
        exported_jobs = 0
        exported_stats = 0

        if sync_assets:
            uploaded_files += _upload_frontend_assets(bucket, asset_version=asset_version)

        if export_feed:
            exported_jobs, feed_uploads = _export_feed(bucket)
            uploaded_files += feed_uploads

    except Exception as e:
        logger.exception("frontend_export_failed", extra={"error": str(e)})
        return {"status": "error", "error": str(e)}

    if export_market_stats:
        try:
            exported_stats, stats_uploads = _export_market_stats(bucket, chart_base_url)
            # stats_uploads = SVG count; +1 for market-stats.json
            uploaded_files += stats_uploads + 1
        except Exception:
            logger.exception("market_stats_export_failed")

    logger.info(
        "frontend_exported_to_gcs",
        extra={
            "job_count": exported_jobs,
            "stats_count": exported_stats,
            "uploaded_files": uploaded_files,
            "sync_assets": sync_assets,
            "export_feed": export_feed,
            "export_market_stats": export_market_stats,
            "asset_version": asset_version,
        },
    )
    return {
        "status": "ok",
        "exported_jobs": exported_jobs,
        "exported_stats": exported_stats,
        "uploaded_files": uploaded_files,
        "synced_assets": sync_assets,
        "exported_feed": export_feed,
        "exported_market_stats": export_market_stats,
        "asset_version": asset_version,
    }
