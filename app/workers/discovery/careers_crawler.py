from __future__ import annotations

import os
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

from app.workers.discovery.ats_probe import probe_ats
from storage.db_engine import get_engine
from storage.repositories.discovery_repository import (
    insert_discovered_company_ats,
    load_discovery_companies,
    update_discovery_last_checked_at,
)

logger = logging.getLogger("openjobseu.discovery")

MAX_COMPANIES_PER_RUN = 10
QUALITY_MIN_JOBS = 1
QUALITY_MIN_REMOTE_HITS = 1
QUALITY_MAX_AGE_DAYS = 120
PROVIDER_PATTERNS: Dict[str, re.Pattern] = {
    "greenhouse": re.compile(
        r"boards\.greenhouse\.io/(?:embed/job_board\?for=)?([a-zA-Z0-9_-]+)",
        re.IGNORECASE,
    ),
    "lever": re.compile(r"jobs\.lever\.co/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    "workable": re.compile(r"apply\.workable\.com/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    "personio": re.compile(r"([a-zA-Z0-9_-]+)\.jobs\.personio\.[a-z]{2,4}", re.IGNORECASE),
    "recruitee": re.compile(r"([a-zA-Z0-9_-]+)\.recruitee\.com", re.IGNORECASE),
    "smartrecruiters": re.compile(r"jobs\.smartrecruiters\.com/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    # JobAdder board IDs are platform-assigned (not derivable from company name),
    # so guessing is not applicable — careers crawler is the only automatic discovery path.
    # Probe requires JOBADDER_API_TOKEN; fallback inserts without probe when token is absent.
    "jobadder": re.compile(r"app\.jobadder\.com/jobboard/([a-zA-Z0-9_-]+)", re.IGNORECASE),
}

# Providers whose probe requires an API token that may not always be present.
# When the token is absent the probe is skipped and the board is inserted
# based solely on the careers-page detection signal.
PROVIDERS_REQUIRING_TOKEN: Dict[str, str] = {
    "jobadder": "JOBADDER_API_TOKEN",
}

INVALID_SLUG_KEYWORDS = {
    "test",
    "demo",
    "example",
    "sample",
    "sandbox",
    "staging",
    "career",
    "careers",
}
JOB_LINK_KEYWORDS = (
    "job",
    "career",
    "work",
    "join",
    "hiring",
    "position",
)
MAX_SECONDARY_LINKS = 5


def _is_valid_slug(slug: str) -> bool:
    slug_lower = slug.lower()
    if len(slug.strip()) < 3:
        return False
    return not any(keyword in slug_lower for keyword in INVALID_SLUG_KEYWORDS)


def _detect_provider(url: str) -> tuple[str, str] | None:
    for provider, pattern in PROVIDER_PATTERNS.items():
        match = pattern.search(url)
        if match:
            slug = match.group(1)
            return provider, slug

    parsed = urlparse(url)

    if "boards.greenhouse.io" in parsed.netloc:
        qs = parse_qs(parsed.query)
        slug = qs.get("for")
        if slug:
            return "greenhouse", slug[0]

    return None


def _is_recent(recent_job_at: Any) -> bool:
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


def _fetch_careers_page(url: str) -> tuple[requests.Response | None, str | None]:
    if not url or not url.startswith(("http://", "https://")):
        return None, "invalid_url"

    parsed_url = urlparse(url)
    host = (parsed_url.hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1") or host.startswith(("192.168.", "10.", "172.")):
        return None, "invalid_url"

    start_time = time.perf_counter()

    # Allow bypassing TLS for specific broken domains (comma-separated list)
    bypass_domains = [d.strip() for d in os.getenv("DISCOVERY_TLS_BYPASS_DOMAINS", "").split(",") if d.strip()]
    verify_tls = parsed_url.hostname not in bypass_domains

    try:
        response = requests.get(url, timeout=15, allow_redirects=True, verify=verify_tls, stream=True)
        response.raise_for_status()

        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > 5 * 1024 * 1024:  # Sztywny limit wielkości do 5MB
                logger.warning("careers page too large, aborting", extra={"url": url})
                return None, "too_large"

        response._content = content  # Bezpieczny "hack", aby response.text i kodowanie zadziałały dla reszty skryptu
        return response, None
    except requests.exceptions.SSLError as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning(
            f"discovery TLS/SSL error [{url}]: {exc}",
            extra={
                "component": "discovery",
                "phase": "careers_discovery",
                "careers_url": url,
                "duration_ms": duration_ms,
                "error_type": "tls_failure",
                "error": str(exc),
            },
        )
        return None, "tls_failure"
    except requests.exceptions.Timeout:
        return None, "timeout"
    except requests.exceptions.TooManyRedirects:
        return None, "redirect_loop"
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning(
            f"discovery fetch careers failed [{url}]: {exc}",
            extra={
                "component": "discovery",
                "phase": "careers_discovery",
                "careers_url": url,
                "duration_ms": duration_ms,
                "error_type": "other_error",
                "error": str(exc),
            },
        )
        return None, "other_error"


def _detect_provider_from_fetch(final_url: str, html: str) -> tuple[str, str] | None:
    detected = _detect_provider(final_url)
    if detected:
        return detected
    return _detect_provider(html)


def _extract_candidate_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for element in soup.find_all("a", href=True):
        href = element["href"].lower()
        text = (element.get_text() or "").lower()
        for keyword in JOB_LINK_KEYWORDS:
            if keyword in href or keyword in text:
                links.append(urljoin(base_url, element["href"]))
                break

    return links[:MAX_SECONDARY_LINKS]


def _detect_provider_from_redirects(
    response: requests.Response,
) -> tuple[str, str] | None:
    urls = [r.url for r in response.history] + [response.url]

    for url in urls:
        detection = _detect_provider(url)
        if detection:
            return detection

    return None


def _detect_provider_with_shallow_crawl(final_url: str, html: str) -> tuple[str, str] | None:
    detection = _detect_provider_from_fetch(final_url, html)
    if detection:
        return detection

    candidate_links = _extract_candidate_links(html, final_url)
    for link in candidate_links:
        response, _ = _fetch_careers_page(link)
        if not response:
            continue

        next_url = response.url
        next_html = response.text
        detection = _detect_provider_from_fetch(next_url, next_html)
        if detection:
            return detection

    return None


def run_careers_discovery() -> Dict[str, int]:
    started = time.perf_counter()

    metrics = {
        "companies_scanned": 0,
        "ats_detected": 0,
        "ats_probed": 0,
        "ats_inserted": 0,
        "ats_inserted_no_probe": 0,
        "ats_skipped_quality": 0,
        "ats_duplicates": 0,
        "errors_tls": 0,
        "errors_timeout": 0,
        "errors_redirect": 0,
        "errors_too_large": 0,
        "errors_other": 0,
        "no_ats_detected": 0,
    }

    try:
        engine = get_engine()
        with engine.connect() as conn:
            rows = load_discovery_companies(conn, phase="careers", limit=MAX_COMPANIES_PER_RUN)

        if not rows:
            return metrics

        total = len(rows)
        for idx, row in enumerate(rows, 1):
            metrics["companies_scanned"] += 1
            company_id = None

            try:
                if hasattr(row, "_mapping"):
                    company_id = str(row._mapping["company_id"])
                    careers_url = row._mapping.get("careers_url")
                elif hasattr(row, "get"):
                    company_id = str(row["company_id"])
                    careers_url = row.get("careers_url")
                else:
                    company_id = str(getattr(row, "company_id", row[0] if isinstance(row, tuple) else ""))
                    careers_url = getattr(row, "careers_url", None)

                if not careers_url:
                    continue

                response, err_reason = _fetch_careers_page(careers_url)

                if err_reason:
                    if err_reason == "tls_failure":
                        metrics["errors_tls"] += 1
                    elif err_reason == "timeout":
                        metrics["errors_timeout"] += 1
                    elif err_reason == "redirect_loop":
                        metrics["errors_redirect"] += 1
                    elif err_reason == "too_large":
                        metrics["errors_too_large"] += 1
                    elif err_reason != "invalid_url":
                        metrics["errors_other"] += 1

                if not response:
                    continue

                final_url = response.url
                body = response.text

                provider_slug = _detect_provider_from_redirects(response)

                if not provider_slug:
                    provider_slug = _detect_provider_with_shallow_crawl(final_url, body)

                if not provider_slug:
                    metrics["no_ats_detected"] += 1
                    continue

                provider, slug = provider_slug
                if not _is_valid_slug(slug):
                    logger.info(
                        "discovery_slug_rejected",
                        extra={
                            "component": "discovery",
                            "phase": "careers_discovery",
                            "slug": slug,
                        },
                    )
                    continue
                metrics["ats_detected"] += 1

                # Providers like JobAdder require an API token to probe.
                # When the token is absent, fall back to inserting the board
                # directly — the careers-page detection is sufficient signal.
                required_token_env = PROVIDERS_REQUIRING_TOKEN.get(provider)
                if required_token_env and not os.environ.get(required_token_env):
                    logger.warning(
                        "discovery_probe_skipped_no_token",
                        extra={
                            "component": "discovery",
                            "phase": "careers_discovery",
                            "provider": provider,
                            "slug": slug,
                            "missing_env": required_token_env,
                        },
                    )
                    with engine.begin() as conn:
                        inserted = insert_discovered_company_ats(
                            conn,
                            company_id=str(company_id),
                            provider=provider,
                            ats_slug=slug,
                            careers_url=careers_url,
                        )
                    if inserted:
                        metrics["ats_inserted_no_probe"] += 1
                    else:
                        metrics["ats_duplicates"] += 1
                    continue

                probe_result = probe_ats(provider, slug)
                metrics["ats_probed"] += 1
                if not probe_result:
                    continue

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
                    inserted = insert_discovered_company_ats(
                        conn,
                        company_id=str(company_id),
                        provider=provider,
                        ats_slug=slug,
                        careers_url=careers_url,
                    )

                if inserted:
                    metrics["ats_inserted"] += 1
                else:
                    metrics["ats_duplicates"] += 1
            except Exception as e:
                logger.error(
                    f"error processing company in careers_crawler [{company_id}]: {e}",
                    exc_info=True,
                    extra={"company_id": company_id, "component": "discovery"},
                )
            finally:
                if company_id:
                    with engine.begin() as conn:
                        update_discovery_last_checked_at(conn, company_id=company_id, phase="careers")

            if total > 0 and (idx % max(1, total // 10) == 0 or idx == total):
                pct = int((idx / total) * 100)
                filled = int(20 * idx / total)
                bar = "█" * filled + "-" * (20 - filled)
                logger.info(f"careers_crawler progress: [{bar}] {pct}% ({idx}/{total})")
    except Exception:
        logger.error(
            "careers_crawler pipeline failed",
            exc_info=True,
            extra={"component": "discovery", "phase": "careers_discovery"},
        )
        raise
    finally:
        metrics["duration_ms"] = int((time.perf_counter() - started) * 1000)
        logger.info(
            "discovery_summary",
            extra={
                "component": "discovery",
                "phase": "careers_discovery",
                **metrics,
            },
        )

    return metrics
