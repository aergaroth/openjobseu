import re
import time
from collections import Counter
from urllib.parse import urljoin

import requests

API_URL = "https://www.arbeitnow.com/api/job-board-api"
REQUEST_TIMEOUT = 30
MAX_PAGES = 5
MAX_RETRIES = 5
RETRY_INITIAL_DELAY_SECONDS = 1.0
RETRY_BACKOFF_MULTIPLIER = 2
REQUEST_THROTTLE_SECONDS = 0.5
MAX_EXAMPLES = 5

EU_WHITELIST = {
    "Austria",
    "Belgium",
    "Bulgaria",
    "Croatia",
    "Cyprus",
    "Czech Republic",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Hungary",
    "Ireland",
    "Italy",
    "Latvia",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Netherlands",
    "Poland",
    "Portugal",
    "Romania",
    "Slovakia",
    "Slovenia",
    "Spain",
    "Sweden",
    "Norway",
    "Iceland",
    "Liechtenstein",
    "Switzerland",
    "United Kingdom",
}

COUNTRY_ALIASES = {
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "great britain": "United Kingdom",
    "england": "United Kingdom",
    "czechia": "Czech Republic",
    "the netherlands": "Netherlands",
    "usa": "United States",
    "u.s.a.": "United States",
    "u.s.": "United States",
    "uae": "United Arab Emirates",
    "drc": "Democratic Republic of the Congo",
    "russia": "Russian Federation",
    "south korea": "Korea, Republic of",
    "north korea": "Korea, Democratic People's Republic of",
    "vietnam": "Viet Nam",
}

NON_EU_COUNTRIES = {
    "Afghanistan",
    "Albania",
    "Algeria",
    "Andorra",
    "Angola",
    "Antigua and Barbuda",
    "Argentina",
    "Armenia",
    "Australia",
    "Azerbaijan",
    "Bahamas",
    "Bahrain",
    "Bangladesh",
    "Barbados",
    "Belarus",
    "Belize",
    "Benin",
    "Bhutan",
    "Bolivia",
    "Bosnia and Herzegovina",
    "Botswana",
    "Brazil",
    "Brunei",
    "Burkina Faso",
    "Burundi",
    "Cambodia",
    "Cameroon",
    "Canada",
    "Cape Verde",
    "Central African Republic",
    "Chad",
    "Chile",
    "China",
    "Colombia",
    "Comoros",
    "Congo",
    "Costa Rica",
    "Cote d'Ivoire",
    "Cuba",
    "Democratic Republic of the Congo",
    "Djibouti",
    "Dominica",
    "Dominican Republic",
    "Ecuador",
    "Egypt",
    "El Salvador",
    "Equatorial Guinea",
    "Eritrea",
    "Eswatini",
    "Ethiopia",
    "Fiji",
    "Gabon",
    "Gambia",
    "Georgia",
    "Ghana",
    "Grenada",
    "Guatemala",
    "Guinea",
    "Guinea-Bissau",
    "Guyana",
    "Haiti",
    "Honduras",
    "India",
    "Indonesia",
    "Iran",
    "Iraq",
    "Israel",
    "Jamaica",
    "Japan",
    "Jordan",
    "Kazakhstan",
    "Kenya",
    "Kiribati",
    "Korea, Democratic People's Republic of",
    "Korea, Republic of",
    "Kuwait",
    "Kyrgyzstan",
    "Laos",
    "Lebanon",
    "Lesotho",
    "Liberia",
    "Libya",
    "Madagascar",
    "Malawi",
    "Malaysia",
    "Maldives",
    "Mali",
    "Marshall Islands",
    "Mauritania",
    "Mauritius",
    "Mexico",
    "Micronesia",
    "Moldova",
    "Monaco",
    "Mongolia",
    "Montenegro",
    "Morocco",
    "Mozambique",
    "Myanmar",
    "Namibia",
    "Nauru",
    "Nepal",
    "New Zealand",
    "Nicaragua",
    "Niger",
    "Nigeria",
    "North Macedonia",
    "Oman",
    "Pakistan",
    "Palau",
    "Panama",
    "Papua New Guinea",
    "Paraguay",
    "Peru",
    "Philippines",
    "Qatar",
    "Russian Federation",
    "Rwanda",
    "Saint Kitts and Nevis",
    "Saint Lucia",
    "Saint Vincent and the Grenadines",
    "Samoa",
    "San Marino",
    "Sao Tome and Principe",
    "Saudi Arabia",
    "Senegal",
    "Serbia",
    "Seychelles",
    "Sierra Leone",
    "Singapore",
    "Solomon Islands",
    "Somalia",
    "South Africa",
    "South Sudan",
    "Sri Lanka",
    "Sudan",
    "Suriname",
    "Syria",
    "Taiwan",
    "Tajikistan",
    "Tanzania",
    "Thailand",
    "Timor-Leste",
    "Togo",
    "Tonga",
    "Trinidad and Tobago",
    "Tunisia",
    "Turkey",
    "Turkmenistan",
    "Tuvalu",
    "Uganda",
    "Ukraine",
    "United Arab Emirates",
    "United States",
    "Uruguay",
    "Uzbekistan",
    "Vanuatu",
    "Venezuela",
    "Viet Nam",
    "Yemen",
    "Zambia",
    "Zimbabwe",
}

KNOWN_COUNTRIES = EU_WHITELIST | NON_EU_COUNTRIES

HYBRID_KEYWORDS = {
    "hybrid",
    "partially remote",
    "partly remote",
}

REMOTE_KEYWORDS = {
    "remote",
    "work from home",
    "wfh",
    "anywhere",
    "worldwide",
}

ONSITE_KEYWORDS = {
    "onsite",
    "on-site",
    "in office",
    "office",
    "on site",
}


def normalize_country(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)
    if text.endswith("."):
        text = text[:-1].strip()
    alias = COUNTRY_ALIASES.get(text.lower())
    if alias:
        return alias
    if text in KNOWN_COUNTRIES:
        return text
    title = text.title()
    alias = COUNTRY_ALIASES.get(title.lower())
    if alias:
        return alias
    if title in KNOWN_COUNTRIES:
        return title
    return None


def extract_location(job):
    location = job.get("location")
    if isinstance(location, str):
        return location.strip()
    if isinstance(location, dict):
        for key in ("display", "name", "label", "city", "country"):
            value = location.get(key)
            if value:
                return str(value).strip()
    return ""


def extract_country(job):
    for key in ("country", "country_name"):
        country = normalize_country(job.get(key))
        if country:
            return country

    location = job.get("location")
    if isinstance(location, dict):
        for key in ("country", "country_name"):
            country = normalize_country(location.get(key))
            if country:
                return country

    location_text = extract_location(job)
    if not location_text:
        return None

    parts = [part.strip() for part in re.split(r"[,/|]", location_text) if part.strip()]
    for part in reversed(parts):
        country = normalize_country(part)
        if country:
            return country

    paren_chunks = re.findall(r"\(([^)]+)\)", location_text)
    for chunk in reversed(paren_chunks):
        country = normalize_country(chunk.strip())
        if country:
            return country

    return normalize_country(location_text)


def classify_work_mode(job):
    remote_value = job.get("remote")

    text_parts = [
        str(job.get("title") or ""),
        str(job.get("location") or ""),
        str(job.get("description") or ""),
    ]
    job_types = job.get("job_types")
    if isinstance(job_types, list):
        text_parts.extend(str(v) for v in job_types if v)

    combined = " ".join(text_parts).lower()

    if any(keyword in combined for keyword in HYBRID_KEYWORDS):
        return "hybrid"

    if isinstance(remote_value, bool):
        if remote_value:
            return "remote"
        if any(keyword in combined for keyword in ONSITE_KEYWORDS):
            return "onsite"
        return "onsite"

    if isinstance(remote_value, str):
        remote_lower = remote_value.lower()
        if "hybrid" in remote_lower:
            return "hybrid"
        if "remote" in remote_lower:
            return "remote"
        if "on-site" in remote_lower or "onsite" in remote_lower:
            return "onsite"

    if any(keyword in combined for keyword in REMOTE_KEYWORDS):
        return "remote"
    if any(keyword in combined for keyword in ONSITE_KEYWORDS):
        return "onsite"

    return "onsite"


def build_next_page_url(current_url, next_value):
    if next_value is None:
        return None

    if isinstance(next_value, int):
        if next_value <= 0:
            return None
        return f"{API_URL}?page={next_value}"

    text = str(next_value).strip()
    if not text or text.lower() in {"null", "none", "false"}:
        return None
    if text.isdigit():
        return f"{API_URL}?page={text}"
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return urljoin(current_url, text)


def extract_next_url(payload, current_url):
    links = payload.get("links")
    if isinstance(links, dict):
        for key in ("next", "next_page_url", "next_url"):
            if key in links:
                return build_next_page_url(current_url, links.get(key))

    for key in ("next_page", "next", "next_page_url"):
        if key in payload:
            return build_next_page_url(current_url, payload.get(key))

    pagination = payload.get("pagination")
    if isinstance(pagination, dict):
        for key in ("next", "next_page", "next_page_url"):
            if key in pagination:
                return build_next_page_url(current_url, pagination.get(key))

    return None


def fetch_page_with_retries(url, page_number):
    delay_seconds = RETRY_INITIAL_DELAY_SECONDS

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            print(
                f"Error fetching page {page_number} "
                f"(attempt {attempt}/{MAX_RETRIES}): {exc}"
            )
            if attempt == MAX_RETRIES:
                print(f"Stopping pagination after repeated errors on page {page_number}.")
                return None, 1
            time.sleep(delay_seconds)
            delay_seconds *= RETRY_BACKOFF_MULTIPLIER
            continue

        if response.status_code == 429:
            if attempt == MAX_RETRIES:
                print(
                    f"Error fetching page {page_number}: HTTP 429 after "
                    f"{MAX_RETRIES} attempts. Stopping pagination."
                )
                return None, 1

            retry_after = response.headers.get("Retry-After")
            retry_after_seconds = None
            if retry_after:
                try:
                    retry_after_seconds = float(retry_after)
                except ValueError:
                    retry_after_seconds = None

            wait_seconds = delay_seconds
            if retry_after_seconds is not None and retry_after_seconds > wait_seconds:
                wait_seconds = retry_after_seconds

            print(
                f"Rate limited on page {page_number} "
                f"(attempt {attempt}/{MAX_RETRIES}), retrying in {wait_seconds:.1f}s..."
            )
            time.sleep(wait_seconds)
            delay_seconds *= RETRY_BACKOFF_MULTIPLIER
            continue

        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            print(f"Error fetching page {page_number}: {exc}")
            return None, 1

        try:
            payload = response.json()
        except ValueError as exc:
            print(f"Error parsing JSON on page {page_number}: {exc}")
            return None, 1

        return payload, 0

    return None, 1


def fetch_all_jobs():
    jobs = []
    next_url = API_URL
    seen_urls = set()
    total_pages_fetched = 0
    total_errors = 0
    page_number = 1

    while (
        next_url
        and next_url not in seen_urls
        and total_pages_fetched < MAX_PAGES
    ):
        print(f"Fetching page {page_number}...")
        seen_urls.add(next_url)

        payload, fetch_errors = fetch_page_with_retries(next_url, page_number)
        total_errors += fetch_errors
        if payload is None:
            break

        page_jobs = payload.get("data")
        if page_jobs is None:
            page_jobs = payload.get("jobs", [])
        if not isinstance(page_jobs, list):
            page_jobs = []
        jobs.extend(page_jobs)
        total_pages_fetched += 1
        print(f"Fetched {len(page_jobs)} jobs")

        next_url = extract_next_url(payload, next_url)
        if next_url and next_url in seen_urls:
            print("Detected repeated pagination URL. Stopping pagination.")
            break

        page_number += 1
        if next_url and total_pages_fetched < MAX_PAGES:
            time.sleep(REQUEST_THROTTLE_SECONDS)

    if total_pages_fetched >= MAX_PAGES and next_url:
        print(f"Reached MAX_PAGES={MAX_PAGES}. Stopping pagination.")

    return jobs, total_pages_fetched, total_errors


def format_job(job, country):
    title = (job.get("title") or "<no title>").strip()
    company = (
        job.get("company_name")
        or job.get("company")
        or job.get("companyTitle")
        or "<no company>"
    )
    location = extract_location(job) or "N/A"
    country_display = country or "N/A"
    return f"- {title} | {company} | location: {location} | country: {country_display}"


def print_examples(label, items):
    print(f"\n{label}:")
    if not items:
        print("- brak")
        return
    for item in items[:MAX_EXAMPLES]:
        print(item)


def main():
    jobs, total_pages_fetched, total_errors = fetch_all_jobs()

    total_jobs = len(jobs)
    mode_counter = Counter()
    jobs_with_country = 0
    jobs_without_country = 0
    eu_country_count = 0
    non_eu_country_count = 0
    missing_location_count = 0

    non_eu_examples = []
    missing_country_examples = []
    onsite_examples = []

    for job in jobs:
        mode = classify_work_mode(job)
        mode_counter[mode] += 1

        location = extract_location(job)
        if not location:
            missing_location_count += 1

        country = extract_country(job)
        if country:
            jobs_with_country += 1
            if country in EU_WHITELIST:
                eu_country_count += 1
            else:
                non_eu_country_count += 1
                if len(non_eu_examples) < MAX_EXAMPLES:
                    non_eu_examples.append(format_job(job, country))
        else:
            jobs_without_country += 1
            if len(missing_country_examples) < MAX_EXAMPLES:
                missing_country_examples.append(format_job(job, country))

        if mode == "onsite" and len(onsite_examples) < MAX_EXAMPLES:
            onsite_examples.append(format_job(job, country))

    print("=== ARBEITNOW AUDIT ===")
    print(f"Total jobs: {total_jobs}")
    print()
    print(f"Remote: {mode_counter['remote']}")
    print(f"Onsite: {mode_counter['onsite']}")
    print(f"Hybrid: {mode_counter['hybrid']}")
    print()
    print(f"With country: {jobs_with_country}")
    print(f"Without country: {jobs_without_country}")
    print()
    print(f"EU countries: {eu_country_count}")
    print(f"Non-EU countries: {non_eu_country_count}")
    print()
    print(f"Missing location: {missing_location_count}")
    print()
    print("=== FINAL SUMMARY ===")
    print(f"total_jobs: {total_jobs}")
    print(f"total_pages_fetched: {total_pages_fetched}")
    print(f"total_errors: {total_errors}")

    print_examples("Przykladowe oferty NON-EU (max 5)", non_eu_examples)
    print_examples("Przykladowe oferty bez country (max 5)", missing_country_examples)
    print_examples("Przykladowe oferty onsite (max 5)", onsite_examples)


if __name__ == "__main__":
    main()
