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
import re
import html

from ingestion.adapters.remoteok_api import RemoteOkApiAdapter
from ingestion.adapters.remotive_api import RemotiveApiAdapter
from ingestion.adapters.weworkremotely_rss import WeWorkRemotelyRssAdapter
from ingestion.adapters.greenhouse_api import GreenhouseApiAdapter


ADAPTERS = {
    "remoteok": RemoteOkApiAdapter,
    "remotive": RemotiveApiAdapter,
    "weworkremotely": WeWorkRemotelyRssAdapter,
    "greenhouse": GreenhouseApiAdapter,
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

    # Prefer `description`, fall back to common alternatives including
    # `content`, `content:encoded`, `summary`, `snippet`.
    desc_candidate = (
        raw.get("description")
        or raw.get("content")
        or raw.get("content:encoded")
        or raw.get("summary")
        or raw.get("snippet")
        or ""
    )

    # feedparser sometimes stores content as a list of dicts with 'value'
    if isinstance(desc_candidate, list):
        parts = []
        for item in desc_candidate:
            if isinstance(item, dict) and "value" in item:
                parts.append(item.get("value") or "")
            elif isinstance(item, str):
                parts.append(item)
        desc_candidate = "\n".join(p for p in parts if p)
    elif isinstance(desc_candidate, dict):
        desc_candidate = (
            desc_candidate.get("value")
            or desc_candidate.get("text")
            or ""
        )

    description = desc_candidate or ""

    if description:
        # Normalize: unescape HTML entities and strip HTML tags for readable output
        description = html.unescape(description)
        description = re.sub(r"<[^>]+>", "", description)
        description = description.strip()
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

    # Special handling for Greenhouse which requires a board_token when
    # constructing the adapter. For greenhouse, expect the identifier to be
    # either "board_token:job_id" (to search a single job) or just
    # "board_token" (to list all jobs on that board).
    adapter_cls = ADAPTERS[source]
    adapter = None

    if source == "greenhouse":
        # support greenhouse:board_token:job_id
        if ":" in source_job_id:
            board_token, source_job_id = source_job_id.split(":", 1)
        else:
            board_token = source_job_id
            # when only board_token is provided, we'll list jobs instead
            source_job_id = None

        try:
            adapter = adapter_cls(board_token)
        except Exception as exc:
            print(f"Failed to initialize Greenhouse adapter: {exc}")
            sys.exit(1)
    else:
        adapter = adapter_cls()

    print(f"Fetching feed from source: {source} ...")
    try:
        raw_items = adapter.fetch()
    except Exception as exc:
        print(f"Failed to fetch from source {source}: {exc}")
        sys.exit(1)

    print(f"Fetched {len(raw_items)} items. Searching for job_id={source_job_id} ...")

    # If user requested a Greenhouse board only (no job id), print a short
    # listing of jobs for that board.
    if source == "greenhouse" and not source_job_id:
        print(f"Listing {len(raw_items)} jobs for greenhouse board '{adapter.board_token}':")
        for raw in raw_items:
            jid = raw.get("id")
            title = raw.get("title") or raw.get("name")
            print(f"- {jid}: {title}")
        return

    for raw in raw_items:
        raw_id = str(raw.get("id"))
        if raw_id == source_job_id:
            print_job(source, raw)
            return

    print("Job not found in current feed.")


if __name__ == "__main__":
    main()
