import logging
import json
import re
import io
import zipfile
import requests
import urllib3

from storage.db_engine import get_engine
from storage.repositories.discovery_repository import insert_source_company, get_existing_brand_names

# Re-exports for compatibility with endpoints  internal.py
from app.workers.discovery.ats_guessing import run_ats_guessing
from app.workers.discovery.careers_crawler import run_careers_discovery
from app.workers.discovery.ats_probe import probe_ats

logger = logging.getLogger("openjobseu.discovery")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

    with engine.connect() as conn:
        existing_names = get_existing_brand_names(conn)

    metrics = {
        "companies_found": 0,
        "companies_inserted": 0,
        "companies_skipped": 0,
    }

    # Aggregate sources
    sources = [
        _fetch_github_remote_companies(),
    ]
    companies = [item for sublist in sources for item in sublist]

    total = len(companies)
    for idx, c in enumerate(companies, 1):
        metrics["companies_found"] += 1

        name = c.get("name") or "Unknown"
        if name.lower() in existing_names:
            metrics["companies_skipped"] += 1
            continue

        homepage = c.get("url")
        if not homepage:
            continue

        candidate_urls = _guess_careers(homepage)
        careers_url = None
        for url in candidate_urls:
            try:
                # Use a HEAD request for efficiency to find the first working URL
                response = requests.head(url, timeout=3, allow_redirects=True, verify=False)
                if response.ok:
                    careers_url = response.url  # Use the final URL after redirects
                    break
            except requests.RequestException:
                continue

        with engine.begin() as conn:
            inserted = insert_source_company(
                conn,
                name=name,
                careers_url=careers_url,
            )

        if inserted:
            metrics["companies_inserted"] += 1
            existing_names.add(name.lower())
            
        if total > 0 and (idx % max(1, total // 10) == 0 or idx == total):
            pct = int((idx / total) * 100)
            filled = int(20 * idx / total)
            bar = "█" * filled + "-" * (20 - filled)
            logger.info(f"company_sources progress: [{bar}] {pct}% ({idx}/{total})")

    logger.info(
        "company_source_discovery",
        extra=metrics
    )

    return metrics
