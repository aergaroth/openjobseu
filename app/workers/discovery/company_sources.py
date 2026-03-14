import logging
import json
import re
import io
import zipfile
import requests

from storage.db_engine import get_engine
from storage.repositories.discovery_repository import insert_source_company

# Re-eksporty dla zachowania kompatybilności z endpointami w internal.py
from app.workers.discovery.ats_guessing import run_ats_guessing
from app.workers.discovery.careers_crawler import run_careers_discovery
from app.workers.discovery.ats_probe import probe_ats

logger = logging.getLogger("openjobseu.discovery")

CAREERS_PATHS = [
    "/careers",
    "/jobs",
    "/join-us",
]


def _guess_careers(homepage: str) -> list[str]:
    """
    Generates a list of potential careers page URLs based on the homepage.
    """
    homepage = homepage.rstrip("/")
    return [homepage + path for path in CAREERS_PATHS]

def _fetch_github_remote_companies():
    """
    Fetches companies from the popular 'remoteintech/remote-jobs' GitHub repository.
    Parses the frontmatter from individual Markdown files via repo ZIP archive.
    """
    url = "https://github.com/remoteintech/remote-jobs/archive/refs/heads/main.zip"
    companies = []
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            for filename in z.namelist():
                if "src/companies/" in filename and filename.endswith(".md"):
                    content = z.read(filename).decode("utf-8")
                    name_match = re.search(r'title:\s*["\']?([^"\'\n]+)', content)
                    url_match = re.search(r'website:\s*["\']?([^"\'\n]+)', content)
                    
                    if name_match and url_match:
                        companies.append({
                            "name": name_match.group(1).strip(),
                            "url": url_match.group(1).strip()
                        })

    except Exception as e:
        logger.warning("Failed to fetch GitHub remote companies", extra={"error": str(e)})

    return companies


def run_company_source_discovery():

    engine = get_engine()

    metrics = {
        "companies_found": 0,
        "companies_inserted": 0,
    }

    # Aggregate sources
    sources = [
        _fetch_github_remote_companies(),
    ]
    companies = [item for sublist in sources for item in sublist]

    for c in companies:

        metrics["companies_found"] += 1

        homepage = c.get("url")
        if not homepage:
            continue

        candidate_urls = _guess_careers(homepage)
        careers_url = None
        for url in candidate_urls:
            try:
                # Use a HEAD request for efficiency to find the first working URL
                response = requests.head(url, timeout=5, allow_redirects=True)
                if response.ok:
                    careers_url = response.url  # Use the final URL after redirects
                    break
            except requests.RequestException:
                continue

        with engine.begin() as conn:
            inserted = insert_source_company(
                conn,
                name=c.get("name") or "Unknown",
                careers_url=careers_url,
            )

        if inserted:
            metrics["companies_inserted"] += 1

    logger.info(
        "company_source_discovery",
        extra=metrics
    )

    return metrics
