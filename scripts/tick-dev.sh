#!/usr/bin/env bash
set -euo pipefail

URL=$(gcloud run services describe dev-openjobseu \
  --project dev-openjobseu \
  --region europe-north1 \
  --format='value(status.url)')

curl -s -X POST "$URL/internal/tick"
