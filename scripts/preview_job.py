"""
Fetches a raw job payload from a given ATS provider and simulates the 
normalization and compliance processing steps, outputting the result to the console.
Useful for debugging ATS mappings and compliance engine rules.
"""

import argparse
import json
import logging
import sys
import re

from app.adapters.ats.registry import get_adapter
from app.domain.jobs.job_processing import process_ingested_job

logger = logging.getLogger(__name__)

def _strip_html(obj):
    if isinstance(obj, dict):
        return {k: _strip_html(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_strip_html(v) for v in obj]
    elif isinstance(obj, str):
        return re.sub(r"<[^>]+>", "", obj)
    return obj

def main():
    parser = argparse.ArgumentParser(description="Preview a raw job from ATS and run compliance on it.")
    parser.add_argument("--provider", required=True, help="ATS provider (e.g., greenhouse, lever, workable)")
    parser.add_argument("--slug", required=True, help="Company ATS slug")
    parser.add_argument("--job-id", required=False, help="Specific Job ID to inspect (optional). If not provided, shows the first job.")
    args = parser.parse_args()

    try:
        adapter = get_adapter(args.provider)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Fetching jobs for '{args.slug}' via '{args.provider}'...\n")
    
    try:
        raw_jobs = adapter.fetch({"ats_slug": args.slug})
    except Exception as e:
        print(f"Failed to fetch jobs: {e}")
        sys.exit(1)

    if not raw_jobs:
        print("No jobs found for this slug.")
        return

    for raw_job in raw_jobs:
        normalized = adapter.normalize(raw_job)
        if not normalized:
            continue
        
        if args.job_id and normalized.get("source_job_id") != args.job_id:
            continue

        print("=" * 80)
        print(f"RAW JOB PAYLOAD (ID: {normalized.get('source_job_id')}):")
        display_raw = _strip_html(raw_job)
        raw_json = json.dumps(display_raw, indent=2, ensure_ascii=False)
        print(raw_json[:3000] + ("\n... [TRUNCATED]" if len(raw_json) > 3000 else ""))

        print("\n" + "=" * 80)
        print("COMPLIANCE & PROCESSING REPORT:")
        processed_job, report = process_ingested_job(normalized, source=f"debug:{args.provider}")
        
        print(json.dumps(report, indent=2, ensure_ascii=False))
        
        print("\nPROCESSED JOB (FINAL):")
        if processed_job:
            processed_job.pop("description", None)  # Omit long description for terminal readability
            print(json.dumps(processed_job, indent=2, ensure_ascii=False))
        else:
            print("Job was REJECTED by policy engine and returned None.")

        # Kończymy po pokazaniu pierwszego dopasowania (lub pierwszej oferty w ogóle)
        break

if __name__ == "__main__":
    main()