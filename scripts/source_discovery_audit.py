"""
Evaluates a specific Greenhouse board token to determine if it is a strong 
candidate for ingestion by analyzing the volume of remote and EU-eligible jobs.
"""

import requests
import time
import sys
from typing import Dict, List

REMOTE_POSITIVE = [
    "fully remote",
    "100% remote",
    "remote role",
    "work from home",
    "home based",
]

REMOTE_WEAK = [
    "remote",
]

REMOTE_NEGATIVE = [
    "do not offer remote",
    "not remote",
    "office-first",
    "office based",
    "office-based",
    "hybrid",
]

EU_EXPLICIT = [
    "europe",
    "eu only",
    "europe only",
    "european union",
]

EU_COUNTRIES = [
    "germany", "france", "poland", "spain", "italy",
    "netherlands", "belgium", "austria", "sweden",
    "denmark", "finland", "czech", "portugal",
    "ireland", "estonia", "latvia", "lithuania",
    "romania", "hungary", "slovenia", "slovakia",
    "croatia", "greece", "cyprus", "malta",
    "luxembourg", "bulgaria",
]

UK_MARKERS = [
    "united kingdom",
    " uk",
    "london",
]

EU_COMPATIBLE = [
    "emea",
    "worldwide",
    "global",
]

NON_EU_MARKERS = [
    "usa only",
    "us only",
    "united states only",
    "canada only",
    "apac only",
    "asia only",
]


def contains_any(text: str, keywords: List[str]) -> bool:
    text = text.lower()
    return any(k in text for k in keywords)


def classify_remote(text: str) -> str:
    text = text.lower()

    if contains_any(text, REMOTE_NEGATIVE):
        return "NON_REMOTE"

    if contains_any(text, REMOTE_POSITIVE):
        return "REMOTE_STRONG"

    if contains_any(text, REMOTE_WEAK):
        return "REMOTE_WEAK"

    return "NO_SIGNAL"


def classify_geo(text: str) -> str:
    text = text.lower()

    if contains_any(text, NON_EU_MARKERS):
        return "NON_EU"

    if contains_any(text, EU_EXPLICIT):
        return "EU_EXPLICIT"

    if contains_any(text, UK_MARKERS):
        return "UK_EXPLICIT"

    if contains_any(text, EU_COUNTRIES):
        return "EU_EXPLICIT"

    if contains_any(text, EU_COMPATIBLE):
        return "EU_COMPATIBLE"

    return "OTHER"


def fetch_greenhouse(board_token: str) -> List[Dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("jobs", [])


def audit_board(board_token: str):
    print(f"\nFetching board: {board_token}")
    start = time.time()
    jobs = fetch_greenhouse(board_token)
    duration = int((time.time() - start) * 1000)

    total = len(jobs)

    remote_counts = {
        "REMOTE_STRONG": 0,
        "REMOTE_WEAK": 0,
        "NON_REMOTE": 0,
        "NO_SIGNAL": 0,
    }

    geo_counts = {
        "EU_EXPLICIT": 0,
        "UK_EXPLICIT": 0,
        "EU_COMPATIBLE": 0,
        "NON_EU": 0,
        "OTHER": 0,
    }

    for job in jobs:
        content = job.get("content") or ""
        location = ""
        raw_loc = job.get("location")
        if isinstance(raw_loc, dict):
            location = raw_loc.get("name") or ""

        text_blob = f"{content} {location}"

        remote_class = classify_remote(text_blob)
        geo_class = classify_geo(text_blob)

        remote_counts[remote_class] += 1
        geo_counts[geo_class] += 1

    print("\n=== DISCOVERY V2 REPORT ===")
    print(f"Total jobs: {total}")
    print(f"Fetch duration: {duration} ms\n")

    print("--- REMOTE SIGNAL ---")
    for k, v in remote_counts.items():
        pct = (v / total * 100) if total else 0
        print(f"{k:15} {v:5} ({pct:5.1f}%)")

    print("\n--- GEO SIGNAL ---")
    for k, v in geo_counts.items():
        pct = (v / total * 100) if total else 0
        print(f"{k:15} {v:5} ({pct:5.1f}%)")

    print("\n--- RECOMMENDATION ---")

    remote_positive = remote_counts["REMOTE_STRONG"] + remote_counts["REMOTE_WEAK"]
    remote_pct = (remote_positive / total * 100) if total else 0

    eu_explicit = geo_counts["EU_EXPLICIT"]
    eu_pct = (eu_explicit / total * 100) if total else 0

    print(f"Remote positive %: {remote_pct:.1f}%")
    print(f"EU explicit %: {eu_pct:.1f}%")

    if remote_pct > 30 and eu_pct > 10:
        print("Candidate: STRONG")
    elif remote_pct > 20:
        print("Candidate: CONDITIONAL (needs EU filtering)")
    else:
        print("Candidate: WEAK")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python source_discovery_audit_v2.py <board_token>")
        sys.exit(1)

    audit_board(sys.argv[1])
