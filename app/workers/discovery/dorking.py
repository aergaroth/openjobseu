import logging
import re
import time
from urllib.parse import urlparse

from app.adapters.ats.registry import get_adapter, list_providers
from app.utils.google_search import google_custom_search
from storage.db_engine import get_engine
from storage.repositories.discovery_repository import insert_discovered_slugs

logger = logging.getLogger(__name__)

def _extract_slug_from_url(url: str, provider: str) -> str | None:
    """
    Extracts an ATS slug from a URL based on the provider's URL structure.
    """
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        path = parsed_url.path

        if not hostname:
            return None

        if provider in ["personio", "recruitee"]:
            # Subdomain-based slug: e.g., https://slug.jobs.personio.com
            match = re.match(r"([^.]+)\.", hostname)
            if match:
                return match.group(1)

        elif provider in ["lever", "greenhouse", "ashby", "workable"]:
            # Path-based slug: e.g., https://jobs.lever.co/slug/ or https://apply.workable.com/slug/
            parts = path.strip("/").split("/")
            if len(parts) > 0 and parts[0]:
                return parts[0]

    except Exception as e:
        logger.warning(f"Failed to parse slug from URL {url} for provider {provider}: {e}")

    return None


def run_dorking_discovery():
    """
    Uses Google Search to discover new ATS slugs for registered providers.
    """
    logger.info("Starting dorking discovery worker.")
    
    providers = list_providers()
    discovered_slugs_all = []

    for provider_name in providers:
        try:
            adapter = get_adapter(provider_name)
            dorking_target = getattr(adapter, 'dorking_target', None)

            if not dorking_target:
                continue

            logger.info(f"Dorking for provider: {provider_name} on target: {dorking_target}")

            query = f'site:{dorking_target} "Europe"'
            
            provider_slugs = set()

            # Paginate through a few pages of search results
            for page in range(1, 4): # 3 pages, 10 results each = 30 total
                start_index = (page - 1) * 10 + 1
                urls = google_custom_search(query, num_results=10, start=start_index)

                if not urls:
                    break

                for url in urls:
                    slug = _extract_slug_from_url(url, provider_name)
                    if slug and slug not in provider_slugs:
                        provider_slugs.add(slug)
                
                # Pacing: Zwalniamy odpytywanie, aby uniknąć limitów HTTP 429 (Too Many Requests)
                # od Google Custom Search API przy iteracji stron.
                time.sleep(1.0)
                
            if provider_slugs:
                logger.info(f"Discovered {len(provider_slugs)} new slugs for {provider_name}.")
                for slug in provider_slugs:
                    discovered_slugs_all.append({
                        "provider": provider_name,
                        "slug": slug,
                        "discovery_source": "dorking",
                    })

            # Dodatkowy krótki bufor przed odpytywaniem o kolejnego dostawcę ATS
            time.sleep(1.0)

        except Exception as e:
            logger.error(f"Error during dorking discovery for provider {provider_name}: {e}")

    if discovered_slugs_all:
        with get_engine().begin() as conn:
            insert_discovered_slugs(conn, discovered_slugs_all)
        logger.info(f"Saved a total of {len(discovered_slugs_all)} discovered slugs to the database.")
    
    logger.info("Dorking discovery worker finished.")
    return {"status": "ok", "discovered_slugs": len(discovered_slugs_all)}
