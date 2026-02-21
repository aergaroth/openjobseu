"""
Audit script for Jobicy API feed.

Usage:
    python scripts/jobicy_audit.py
"""

import requests
from collections import Counter

API_URL = "https://jobicy.com/api/v2/remote-jobs"
COUNT = 100

HEADERS = {
    "User-Agent": "OpenJobsEU-Audit/1.0 (+https://openjobseu.org)"
}

EU_KEYWORDS = [
    "europe",
    "eu",
    "emea",
    "germany",
    "france",
    "spain",
    "italy",
    "poland",
    "netherlands",
    "sweden",
    "finland",
    "austria",
    "belgium",
    "czech",
    "romania",
    "portugal",
    "ireland",
    "denmark",
    "slovakia",
    "slovenia",
    "estonia",
    "latvia",
    "lithuania",
    "hungary",
    "croatia",
    "bulgaria",
    "greece",
    "cyprus",
    "malta",
    "luxembourg",
]

NON_EU_HARD = [
    "usa",
    "united states",
    "canada",
    "north america",
    "apac",
]


def contains_any(text, keywords):
    if not text:
        return False
    text = text.lower()
    return any(k in text for k in keywords)


def fetch_jobs():
    params = {"count": COUNT}
    response = requests.get(API_URL, headers=HEADERS, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    # API sometimes wraps jobs under "jobs" or returns list directly
    if isinstance(data, dict):
        return data.get("jobs", [])
    return data


def classify_geo(job_geo):
    if not job_geo:
        return "unknown"

    geo = job_geo.lower()

    if geo in ("anywhere", "worldwide"):
        return "anywhere"

    if contains_any(geo, NON_EU_HARD):
        return "non_eu_restricted"

    if contains_any(geo, EU_KEYWORDS):
        return "eu_explicit"

    return "other"


def main():
    print("Fetching Jobicy jobs...\n")

    try:
        jobs = fetch_jobs()
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return

    print(f"Fetched {len(jobs)} jobs\n")

    geo_counter = Counter()
    samples = {
        "non_eu_restricted": [],
        "eu_explicit": [],
        "other": [],
    }

    for job in jobs:
        geo = job.get("jobGeo")
        classification = classify_geo(geo)
        geo_counter[classification] += 1

        if classification in samples and len(samples[classification]) < 5:
            samples[classification].append(
                f"{job.get('jobTitle')} | {job.get('companyName')} | geo={geo}"
            )

    print("=== JOBICY GEO AUDIT ===\n")

    total = sum(geo_counter.values())

    for key, value in geo_counter.items():
        percent = (value / total * 100) if total else 0
        print(f"{key:<20} {value:<5} ({percent:.2f}%)")

    print("\n--- Sample NON_EU_RESTRICTED ---")
    for s in samples["non_eu_restricted"]:
        print("-", s)

    print("\n--- Sample EU_EXPLICIT ---")
    for s in samples["eu_explicit"]:
        print("-", s)

    print("\n--- Sample OTHER ---")
    for s in samples["other"]:
        print("-", s)


if __name__ == "__main__":
    main()
