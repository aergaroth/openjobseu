#!/usr/bin/env python3
"""Publikuje statyczne assety frontendu do publicznego bucketa GCS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.workers.frontend_exporter import run_frontend_export


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Publish frontend/index.html, frontend/style.css i frontend/feed.js to the public bucket.")
    )
    parser.add_argument(
        "--release-version",
        default=None,
        help="Optional cache-busting version injected into index.html as ?v=<release-version>.",
    )
    parser.add_argument(
        "--also-export-feed",
        action="store_true",
        help="Also refresh feed.json in the same invocation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_frontend_export(
        sync_assets=True,
        asset_version=args.release_version,
        export_feed=args.also_export_feed,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
