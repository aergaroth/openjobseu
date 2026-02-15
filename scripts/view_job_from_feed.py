#!/usr/bin/env python3

"""
Tool for autition rejected jobs from sources

usage:
python scripts/view_job_from_feed.py remoteok:1130232

"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pprint import pprint

from app.workers.ingestion.remoteok import RemoteOkApiAdapter
from app.workers.ingestion.remotive import RemotiveApiAdapter
from app.workers.ingestion.weworkremotely import WeWorkRemotelyRssAdapter


ADAPTERS = {
    "remoteok": RemoteOkApiAdapter,
    "remotive": RemotiveApiAdapter,
    "weworkremotely": WeWorkRemotelyRssAdapter,
}


def print_job(source: str, raw: dict):
    print("=" * 80)
    print(f"SOURCE: {source}")
    print("=" * 80)

    title = raw.get("position") or raw.get("title")
    company = raw.get("company")
    location = raw.get("location")
    url = raw.get("url") or raw.get("apply_url")

    print(f"Title:     {title}")
    print(f"Company:   {company}")
    print(f"Location:  {location}")
    print(f"URL:       {url}")
    print("-" * 80)

    description = raw.get("description", "")
    if description:
        print("Description (first 800 chars):")
        print(description[:800])
    else:
        print("No description found.")

    print("\nRAW payload keys:")
    print(list(raw.keys()))
    print("=" * 80)


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/view_job_from_feed.py <source:job_id>")
        print("Example: python scripts/view_job_from_feed.py remoteok:1130232")
        sys.exit(1)

    full_id = sys.argv[1]

    if ":" not in full_id:
        print("Invalid format. Expected source:job_id")
        sys.exit(1)

    source, source_job_id = full_id.split(":", 1)

    if source not in ADAPTERS:
        print(f"Unknown source: {source}")
        print(f"Available sources: {list(ADAPTERS.keys())}")
        sys.exit(1)

    adapter = ADAPTERS[source]()

    print(f"Fetching feed from source: {source} ...")
    raw_items = adapter.fetch()

    print(f"Fetched {len(raw_items)} items. Searching for job_id={source_job_id} ...")

    for raw in raw_items:
        raw_id = str(raw.get("id"))
        if raw_id == source_job_id:
            print_job(source, raw)
            return

    print("Job not found in current feed.")


if __name__ == "__main__":
    main()
