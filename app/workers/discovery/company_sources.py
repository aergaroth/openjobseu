import logging
import json
import re
import uuid
import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

from storage.db_engine import get_engine

logger = logging.getLogger("openjobseu.discovery")

CAREERS_PATHS = [
    "/careers",
    "/jobs",
    "/join-us",
]


def _guess_careers(homepage: str) -> str | None:
    homepage = homepage.rstrip("/")
    # The original implementation had a bug where it would return on the first
    # iteration of the loop. This version just returns the first guess, which
    # is equivalent but clearer.
    if CAREERS_PATHS:
        return homepage + CAREERS_PATHS[0]
    return None

def _fetch_yc_companies():
    """
    Fetches company data from YC's public directory API.
    It handles pagination to retrieve all companies for the specified region.
    """
    companies = []
    page = 1
    known_non_company_paths = {"/companies/jobs", "/companies/launches", "/companies/new", "/companies/exits", "/companies/top"}

    while True:
        try:
            # YC uses a browse API to dynamically load companies.
            response = requests.get(
                "https://www.ycombinator.com/companies/browse",
                params={"page": page, "regions[]": "Europe"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()

            soup = BeautifulSoup(data["html"], "html.parser")

            page_companies = []
            # The links to company profiles are of the form /companies/<slug>
            for tag in soup.find_all("a", href=lambda href: href and href.startswith("/companies/")):
                href = tag["href"]

                # Filter out general links like /companies/jobs or /companies/top/private
                if href.count('/') > 2 or href in known_non_company_paths:
                    continue

                name = tag.get_text(strip=True)
                if not name:
                    continue

                page_companies.append({
                    "name": name,
                    "profile": "https://www.ycombinator.com" + href,
                })

            if not page_companies:
                break

            companies.extend(page_companies)

            if not data.get("hasMore"):
                break
            page += 1
        except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
            logger.warning("Failed to fetch or parse YC companies page.", extra={"page": page, "error": str(e)})
            break

    # dedupe
    unique = {c["profile"]: c for c in companies}

    return list(unique.values())


def _fetch_company_homepage(profile_url):

    try:
        response = requests.get(profile_url, timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")

        website = soup.find("a", {"rel": "noopener"})
        if website:
            return website["href"]

    except Exception:
        return None

    return None


def _fetch_github_remote_companies():
    """
    Fetches companies from the popular 'remoteintech/remote-jobs' GitHub repository.
    Parses the raw Markdown content.
    """
    url = "https://raw.githubusercontent.com/remoteintech/remote-jobs/main/README.md"
    companies = []
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Regex to find markdown links mostly in table rows or lists: [Name](http...)
        # This is a heuristic approach.
        # Matches: [CompanyName](http://example.com)
        pattern = re.compile(r"\[(?P<name>[^\]]+)\]\((?P<url>https?://[^)]+)\)")
        
        for line in response.text.splitlines():
            # Skip header lines or table definitions often found in READMEs
            if "---" in line or "Name" in line and "|" in line:
                continue
                
            for match in pattern.finditer(line):
                companies.append(match.groupdict())

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
        _fetch_yc_companies(),
        _fetch_github_remote_companies(),
    ]
    companies = [item for sublist in sources for item in sublist]

    for c in companies:

        metrics["companies_found"] += 1

        homepage = None
        if "profile" in c:
            homepage = _fetch_company_homepage(c["profile"])
        
        if not homepage:
            homepage = c.get("url")
            if not homepage:
                continue

        careers_url = _guess_careers(homepage)

        with engine.begin() as conn:

            stmt = text("""
                INSERT INTO companies (
                    company_id,
                    brand_name,
                    legal_name,
                    careers_url,
                    is_active,
                    bootstrap,
                    created_at,
                    updated_at
                )
                VALUES (
                    :uid, :name, :name, :careers_url, true, false, NOW(), NOW()
                )
                ON CONFLICT DO NOTHING
                RETURNING company_id
            """)
            result = conn.execute(stmt, {
                "uid": uuid.uuid4(),
                "name": c.get("name") or "Unknown",
                "careers_url": careers_url,
            })
            inserted = result.fetchone() is not None

        if inserted:
            metrics["companies_inserted"] += 1

    logger.info(
        "company_source_discovery",
        extra=metrics
    )

    return metrics
