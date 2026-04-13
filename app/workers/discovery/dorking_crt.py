"""
Certificate Transparency log discovery via crt.sh.

Finds subdomains of ATS providers by querying the public CT log database.
Only works for subdomain-based providers (traffit, personio, recruitee, teamtailor-like).
No API key required, no rate limits beyond polite delays.
"""

import logging
import re
import time

import requests

from app.adapters.ats.registry import get_adapter, list_providers
from storage.db_engine import get_engine
from storage.repositories.discovery_repository import insert_discovered_slugs

logger = logging.getLogger(__name__)

# Providers whose slug is a subdomain of dorking_target (e.g. slug.traffit.com)
SUBDOMAIN_PROVIDERS = {"traffit", "personio", "recruitee", "breezy"}

# Subdomains that are infra/service noise, not company job boards
_NOISE = {
    "www",
    "mail",
    "smtp",
    "api",
    "app",
    "dev",
    "staging",
    "test",
    "beta",
    "cdn",
    "static",
    "media",
    "assets",
    "dashboard",
    "admin",
    "portal",
    "jobs",
    "careers",
    "help",
    "support",
    "docs",
    "status",
}

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")


def _fetch_crt_slugs(dorking_target: str) -> set[str]:
    """Queries crt.sh for all certificates issued for *.{dorking_target}."""
    url = "https://crt.sh/"
    params = {"q": f"%.{dorking_target}", "output": "json"}

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        entries = resp.json()
    except Exception as e:
        logger.warning(f"crt.sh request failed for {dorking_target}: {e}")
        return set()

    slugs: set[str] = set()
    for entry in entries:
        for raw in (entry.get("name_value") or "").splitlines():
            name = raw.strip().lstrip("*").lstrip(".").lower()
            # Keep only the leftmost label (the company subdomain)
            subdomain = name.split(".")[0]
            if subdomain and subdomain not in _NOISE and _SLUG_RE.match(subdomain):
                slugs.add(subdomain)

    return slugs


def run_dorking_crt_discovery() -> dict[str, int]:
    """Discovers ATS slugs for subdomain-based providers via Certificate Transparency logs."""
    discovered_slugs_all: list[dict] = []

    for provider_name in list_providers():
        if provider_name not in SUBDOMAIN_PROVIDERS:
            continue

        try:
            adapter = get_adapter(provider_name)
            dorking_target = getattr(adapter, "dorking_target", None)
            if not dorking_target:
                continue

            logger.info(f"crt.sh dorking for {provider_name} ({dorking_target})")
            slugs = _fetch_crt_slugs(dorking_target)

            for slug in slugs:
                discovered_slugs_all.append({"provider": provider_name, "slug": slug, "discovery_source": "crt_sh"})

            logger.info(f"crt.sh found {len(slugs)} slug candidates for {provider_name}")
            time.sleep(2.0)  # polite delay between providers

        except Exception as e:
            logger.error(f"crt.sh discovery error for {provider_name}: {e}", exc_info=True)

    if discovered_slugs_all:
        with get_engine().begin() as conn:
            insert_discovered_slugs(conn, discovered_slugs_all)

    logger.info(
        "dorking_crt_done",
        extra={"component": "discovery", "phase": "dorking_crt", "discovered_slugs": len(discovered_slugs_all)},
    )
    return {"discovered_slugs": len(discovered_slugs_all)}
