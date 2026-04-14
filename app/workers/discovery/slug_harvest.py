from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urlparse, urljoin, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from storage.db_engine import get_engine
from storage.repositories.discovery_repository import (
    insert_discovered_slugs,
    insert_discovered_slug,
    update_discovered_slug_status,
    load_discovery_companies,
)

logger = logging.getLogger("openjobseu.discovery")

MAX_COMPANIES_PER_RUN = 20
MAX_SECONDARY_LINKS = 5
MAX_URLS_PER_COMPANY = 12

# Polite defaults (compliance: robots + rate limit)
USER_AGENT = "OpenJobsEU/1.0 (https://openjobseu.org)"
MIN_SECONDS_BETWEEN_REQUESTS_PER_HOST = 1.0
ROBOTS_CACHE_TTL_SECONDS = 24 * 3600

# Hard limits to avoid storing/processing too much (no-PII storage)
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class SlugCandidate:
    provider: str
    slug: str
    evidence: str  # "final_url" | "redirect" | "html" | "link"


_INVALID_SLUG_KEYWORDS = {"test", "demo", "example", "sample", "sandbox", "staging"}
_NOISE_SUBDOMAINS = {"www", "jobs", "careers", "career", "app", "api", "admin", "static", "cdn"}


_PATTERNS: dict[str, re.Pattern] = {
    "traffit": re.compile(r"https?://([a-z0-9][a-z0-9-]{1,62}[a-z0-9])\.traffit\.com", re.I),
    "breezy": re.compile(r"https?://([a-z0-9][a-z0-9-]{1,62}[a-z0-9])\.breezy\.hr", re.I),
    "jobadder": re.compile(r"https?://app\.jobadder\.com/jobboard/([a-zA-Z0-9_-]+)", re.I),
    # Teamtailor public career sites are typically hosted on *.teamtailor.com with /jobs routes.
    # Token is not derivable; we only collect the account subdomain as a candidate.
    "teamtailor": re.compile(
        r"https?://([a-z0-9-]+)\.teamtailor\.com/(?:[a-z]{2}(?:-[A-Z]{2})?/)?jobs(?:/|\b|\?|$)",
        re.I,
    ),
}


class RobotsCache:
    def __init__(self):
        self._cache: dict[str, tuple[float, RobotFileParser]] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host:
            return False

        now = time.time()
        entry = self._cache.get(host)
        if entry and (now - entry[0]) < ROBOTS_CACHE_TTL_SECONDS:
            rp = entry[1]
            return rp.can_fetch(USER_AGENT, url)

        rp = RobotFileParser()
        robots_url = urlunparse((parsed.scheme or "https", host, "/robots.txt", "", "", ""))
        try:
            resp = requests.get(
                robots_url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                stream=True,
            )
            content = b""
            for chunk in resp.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > 256 * 1024:
                    break
            rp.parse(content.decode("utf-8", errors="replace").splitlines())
        except Exception:
            # Fail-safe: if robots cannot be fetched/parsed, treat as disallow.
            rp.parse(["User-agent: *", "Disallow: /"])

        self._cache[host] = (now, rp)
        return rp.can_fetch(USER_AGENT, url)


class HostRateLimiter:
    def __init__(self):
        self._last: dict[str, float] = {}

    def wait(self, url: str) -> None:
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return
        now = time.monotonic()
        last = self._last.get(host)
        if last is not None:
            elapsed = now - last
            if elapsed < MIN_SECONDS_BETWEEN_REQUESTS_PER_HOST:
                time.sleep(MIN_SECONDS_BETWEEN_REQUESTS_PER_HOST - elapsed)
        self._last[host] = time.monotonic()


def _strip_query(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


def _is_valid_slug(slug: str) -> bool:
    s = (slug or "").strip()
    if len(s) < 3:
        return False
    s_lower = s.lower()
    if any(k in s_lower for k in _INVALID_SLUG_KEYWORDS):
        return False
    return True


def _extract_candidates_from_text(text: str, evidence: str) -> list[SlugCandidate]:
    out: list[SlugCandidate] = []
    if not text:
        return out
    for provider, pattern in _PATTERNS.items():
        for match in pattern.finditer(text):
            slug = (match.group(1) or "").strip()
            if provider == "teamtailor":
                slug_lower = slug.lower()
                if slug_lower in _NOISE_SUBDOMAINS:
                    continue
            if _is_valid_slug(slug):
                out.append(SlugCandidate(provider=provider, slug=slug, evidence=evidence))
    return out


def _score_candidate(c: SlugCandidate, occurrences: int, from_final_url: bool) -> int:
    score = 0
    if from_final_url:
        score += 2
    if occurrences >= 2:
        score += 1
    if any(k in c.slug.lower() for k in _INVALID_SLUG_KEYWORDS):
        score -= 1
    return score


def _extract_candidate_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "")
        if not href:
            continue
        links.append(urljoin(base_url, href))
        if len(links) >= MAX_SECONDARY_LINKS:
            break
    return links


def _fetch(url: str, *, robots: RobotsCache, limiter: HostRateLimiter) -> tuple[requests.Response | None, str | None]:
    if not url or not url.startswith(("http://", "https://")):
        return None, "invalid_url"

    url = _strip_query(url)
    if not robots.can_fetch(url):
        return None, "robots_disallow"

    limiter.wait(url)
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            stream=True,
        )
        resp.raise_for_status()
        content = b""
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_RESPONSE_BYTES:
                return None, "too_large"
        resp._content = content
        return resp, None
    except requests.exceptions.Timeout:
        return None, "timeout"
    except requests.exceptions.TooManyRedirects:
        return None, "redirect_loop"
    except Exception:
        return None, "fetch_error"


def _dedupe_candidates(cands: Iterable[SlugCandidate]) -> dict[tuple[str, str], list[SlugCandidate]]:
    grouped: dict[tuple[str, str], list[SlugCandidate]] = {}
    for c in cands:
        key = (c.provider, c.slug)
        grouped.setdefault(key, []).append(c)
    return grouped


def run_slug_harvest() -> dict[str, int]:
    started = time.perf_counter()
    metrics: dict[str, int] = {
        "companies_scanned": 0,
        "urls_fetched": 0,
        "robots_blocked": 0,
        "candidates_found": 0,
        "candidates_saved": 0,
        "teamtailor_candidates_saved": 0,
        "errors": 0,
    }

    engine = get_engine()
    robots = RobotsCache()
    limiter = HostRateLimiter()

    with engine.connect() as conn:
        companies = load_discovery_companies(conn, phase="careers", limit=MAX_COMPANIES_PER_RUN)

    bulk_rows: list[dict[str, Any]] = []

    for row in companies:
        metrics["companies_scanned"] += 1

        if hasattr(row, "_mapping"):
            company_id = str(row._mapping.get("company_id") or "")
            careers_url = row._mapping.get("careers_url")
        elif hasattr(row, "get"):
            company_id = str(row.get("company_id") or "")
            careers_url = row.get("careers_url")
        else:
            company_id = str(getattr(row, "company_id", ""))
            careers_url = getattr(row, "careers_url", None)

        if not careers_url:
            continue

        to_visit: list[str] = [str(careers_url)]
        visited: set[str] = set()
        found: list[SlugCandidate] = []

        while to_visit and len(visited) < MAX_URLS_PER_COMPANY:
            url = to_visit.pop(0)
            clean = _strip_query(url)
            if clean in visited:
                continue
            visited.add(clean)

            resp, err = _fetch(clean, robots=robots, limiter=limiter)
            if err == "robots_disallow":
                metrics["robots_blocked"] += 1
                continue
            if not resp:
                if err not in ("invalid_url",):
                    metrics["errors"] += 1
                continue

            metrics["urls_fetched"] += 1

            # Evidence: final URL and redirects
            final_url = _strip_query(resp.url)
            found.extend(_extract_candidates_from_text(final_url, evidence="final_url"))
            for h in resp.history or []:
                found.extend(_extract_candidates_from_text(_strip_query(h.url), evidence="redirect"))

            html = resp.text or ""
            # Evidence: HTML body
            found.extend(_extract_candidates_from_text(html, evidence="html"))

            # Shallow crawl: add a few candidate links
            for link in _extract_candidate_links(html, final_url):
                link_clean = _strip_query(link)
                found.extend(_extract_candidates_from_text(link_clean, evidence="link"))
                if link_clean not in visited and len(to_visit) < MAX_URLS_PER_COMPANY:
                    to_visit.append(link_clean)

        grouped = _dedupe_candidates(found)
        metrics["candidates_found"] += sum(len(v) for v in grouped.values())

        for (provider, slug), items in grouped.items():
            occurrences = len(items)
            from_final = any(i.evidence == "final_url" for i in items)
            score = _score_candidate(items[0], occurrences=occurrences, from_final_url=from_final)
            if score < 2:
                continue

            if provider == "teamtailor":
                # Teamtailor API requires per-company token; store candidates as needs_token.
                with engine.begin() as conn:
                    inserted_id = insert_discovered_slug(
                        conn,
                        provider="teamtailor",
                        slug=slug,
                        discovery_source="slug_harvest",
                    )
                    if inserted_id is not None:
                        update_discovered_slug_status(conn, inserted_id, "needs_token")
                        metrics["teamtailor_candidates_saved"] += 1
                continue

            bulk_rows.append({"provider": provider, "slug": slug, "discovery_source": "slug_harvest"})

    if bulk_rows:
        with engine.begin() as conn:
            insert_discovered_slugs(conn, bulk_rows)
        metrics["candidates_saved"] = len(bulk_rows)

    metrics["duration_ms"] = int((time.perf_counter() - started) * 1000)
    logger.info("slug_harvest_done", extra={"component": "discovery", "phase": "slug_harvest", **metrics})
    return metrics

