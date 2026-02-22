import requests
from collections import Counter

FEED_URL = "http://localhost:8000/jobs/feed"

EU_COUNTRIES = [
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
    "United Kingdom"
]

def classify(job):
    scope = (job.get("remote_scope") or "").lower()
    text = scope

    if any(k in text for k in ["us only", "usa only", "north america only"]):
        return "EU_INCOMPATIBLE"

    if any(country in text for country in EU_COUNTRIES):
        return "EU_EXPLICIT"

    if "europe" in text or "eu" in text:
        return "EU_EXPLICIT"

    if "americas" in text and "europe" in text:
        return "EU_MIXED"

    if "worldwide" in text:
        return "EU_COMPATIBLE"

    if not text.strip():
        return "EU_UNKNOWN"

    return "EU_UNKNOWN"


def main():
    print(f"Fetching feed: {FEED_URL}")
    r = requests.get(FEED_URL)
    r.raise_for_status()
    data = r.json()

    jobs = data["jobs"]
    counter = Counter()

    samples = {}

    for job in jobs:
        cls = classify(job)
        counter[cls] += 1

        if cls not in samples:
            samples[cls] = job

    print("\n=== EU SCOPE AUDIT ===\n")

    total = len(jobs)
    for k, v in counter.items():
        percent = round((v / total) * 100, 2)
        print(f"{k:16} {v:4}  ({percent}%)")

    print("\n--- Sample examples ---\n")

    for cls, job in samples.items():
        print(f"{cls}:")
        print(f"  {job['title']} | {job['company']} | {job['remote_scope']}")
        print()


if __name__ == "__main__":
    main()
