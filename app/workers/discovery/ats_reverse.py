from __future__ import annotations

import logging
import os
import requests
import time
from datetime import datetime, timezone, timedelta


from app.workers.discovery.ats_probe import probe_ats
from storage.db_engine import get_engine
from storage.repositories.discovery_repository import (
    check_ats_exists,
    get_or_create_placeholder_company,
    insert_discovered_company_ats,
)

logger = logging.getLogger("openjobseu.discovery")

QUALITY_MIN_JOBS = 1
QUALITY_MIN_REMOTE_HITS = 0
QUALITY_MAX_AGE_DAYS = 120

# Initial dictionary (in the future, slugs can be loaded dynamically, e.g., from a file or permutations of existing names)
POPULAR_SLUGS = [
    "stripe",
    "notion",
    "figma",
    "datadog",
    "shopify",
    "revolut",
    "wise",
    "bolt",
    "klarna",
    "n26",
    "openai",
    "deepmind",
    "anthropic",
    "vercel",
    "miro",
    "gitlab",
    "github",
    "discord",
    "canva",
    "monday",
    "reddit",
    "pinterest",
    "airbnb",
    "doordash",
    "uber",
    "spotify",
    "lyft",
    "dropbox",
    "coinbase",
    "plaid",
    "robinhood",
    "chime",
    "brex",
    "ramp",
    "gusto",
    "rippling",
    "deel",
    "checkr",
    "fivetran",
    "gocardless",
    # European startups and scale-ups (often using Ashby/Lever/Greenhouse)
    "alan",
    "qonto",
    "doctolib",
    "pigment",
    "payfit",
    "swile",
    "vinted",
    "traderepublic",
    "bitpanda",
    "personio",
    "contentful",
    "aiven",
    "pleo",
    "mollie",
    "lokalise",
    "truelayer",
    "huggingface",
    "printify",
    "gorgias",
    "yousign",
]

PROVIDERS_TO_PROBE = [
    "greenhouse",
    "lever",
    "workable",
    "ashby",
    "smartrecruiters",
    "traffit",
    "breezy",
]


def _fallback_company_name(slug: str) -> str:
    return str(slug or "").replace("-", " ").replace("_", " ").strip().title()


def _resolve_company_name(probe_result: dict, slug: str) -> str:
    raw_name = probe_result.get("company_name") if isinstance(probe_result, dict) else None
    name = str(raw_name or "").strip()
    return name or _fallback_company_name(slug)


def _load_slugs() -> list[str]:
    """Loads slugs from an external URL if configured, falling back to POPULAR_SLUGS."""
    slugs = set(POPULAR_SLUGS)
    url = os.environ.get("ATS_REVERSE_SLUGS_URL")

    if url:
        try:
            # stream=True zapobiega wczytaniu wielkiego pliku do RAM
            response = requests.get(url, timeout=10, stream=True)
            response.raise_for_status()

            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > 1024 * 1024:  # Sztywny limit wielkości do 1MB
                    raise ValueError("External slugs file is too large (>1MB)")

            text_data = content.decode("utf-8", errors="replace")
            added_count = 0

            for line in text_data.splitlines():
                if added_count >= 5000:  # Zabezpieczenie przed "zadławieniem" pętli workera
                    logger.warning("Max slugs limit reached, truncating parsing.")
                    break

                clean_slug = line.strip()
                if clean_slug and not clean_slug.startswith("#"):
                    slugs.add(clean_slug)
                    added_count += 1
            logger.info("external_slugs_loaded", extra={"url": url, "total_slugs": len(slugs)})
        except Exception as exc:
            logger.warning("external_slugs_fetch_failed", extra={"url": url, "error": str(exc)})

    return sorted(list(slugs))


def _is_recent(recent_job_at: object) -> bool:
    if not recent_job_at:
        return True
    if isinstance(recent_job_at, str):
        try:
            recent_job_at = datetime.fromisoformat(recent_job_at.replace("Z", "+00:00"))
        except ValueError:
            pass
    if not isinstance(recent_job_at, datetime):
        return True
    if recent_job_at.tzinfo is None:
        recent_job_at = recent_job_at.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=QUALITY_MAX_AGE_DAYS)
    return recent_job_at >= cutoff


def run_ats_reverse_discovery() -> dict[str, int]:
    started = time.perf_counter()
    metrics = {
        "slugs_tested": 0,
        "ats_detected": 0,
        "ats_inserted": 0,
        "ats_skipped_quality": 0,
        "ats_duplicates": 0,
    }

    try:
        engine = get_engine()
        slugs_to_test = _load_slugs()
        total = len(PROVIDERS_TO_PROBE) * len(slugs_to_test)
        idx = 0

        for provider in PROVIDERS_TO_PROBE:
            for slug in slugs_to_test:
                idx += 1
                try:
                    # Deduplication check before querying API to save requests
                    with engine.connect() as conn:
                        if check_ats_exists(conn, provider, slug):
                            metrics["ats_duplicates"] += 1
                            continue

                    metrics["slugs_tested"] += 1
                    probe_result = probe_ats(provider, slug)
                    if not probe_result:
                        continue

                    metrics["ats_detected"] += 1

                    try:
                        jobs_total = int(probe_result.get("jobs_total") or 0)
                    except (ValueError, TypeError):
                        jobs_total = 0

                    try:
                        remote_hits = int(probe_result.get("remote_hits") or 0)
                    except (ValueError, TypeError):
                        remote_hits = 0

                    recent_job_at = probe_result.get("recent_job_at")

                    if (
                        jobs_total < QUALITY_MIN_JOBS
                        or remote_hits < QUALITY_MIN_REMOTE_HITS
                        or not _is_recent(recent_job_at)
                    ):
                        metrics["ats_skipped_quality"] += 1
                        continue

                    with engine.begin() as conn:
                        name = _resolve_company_name(probe_result, slug)
                        company_id = get_or_create_placeholder_company(conn, name)

                        inserted = insert_discovered_company_ats(
                            conn,
                            company_id=company_id,
                            provider=provider,
                            ats_slug=slug,
                            careers_url=None,
                        )

                    if inserted:
                        metrics["ats_inserted"] += 1
                    else:
                        metrics["ats_duplicates"] += 1

                except Exception as e:
                    logger.error(
                        f"error processing slug in ats_reverse [{provider}/{slug}]: {e}",
                        exc_info=True,
                        extra={
                            "provider": provider,
                            "slug": slug,
                            "component": "discovery",
                        },
                    )

                if total > 0 and (idx % max(1, total // 10) == 0 or idx == total):
                    pct = int((idx / total) * 100)
                    filled = int(20 * idx / total)
                    bar = "█" * filled + "-" * (20 - filled)
                    logger.info(f"ats_reverse progress: [{bar}] {pct}% ({idx}/{total})")
    except Exception:
        logger.error(
            "ats_reverse pipeline failed",
            exc_info=True,
            extra={"component": "discovery", "phase": "ats_reverse"},
        )
        raise
    finally:
        metrics["duration_ms"] = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ats_reverse_discovery_summary",
            extra={
                "component": "discovery",
                "phase": "ats_reverse",
                **metrics,
            },
        )

    return metrics
