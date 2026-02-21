#!/usr/bin/env sh
set -eu

# Priority:
# 1) explicit TICK_URL
# 2) Cloud Run URL via gcloud (if available)
# 3) fixed Cloud Run URL fallback
# 4) local runtime URL fallback

FIXED_CLOUD_RUN_URL="https://dev-openjobseu-53442084713.europe-north1.run.app"
LOCAL_URL="http://127.0.0.1:${PORT:-8000}"

append_candidate() {
  candidate="${1%/}"
  if [ -n "$candidate" ]; then
    CANDIDATES="${CANDIDATES} ${candidate}"
  fi
}

CANDIDATES=""

if [ -n "${TICK_URL:-}" ]; then
  append_candidate "${TICK_URL}"
fi

if command -v gcloud >/dev/null 2>&1; then
  GCLOUD_URL="$(gcloud run services describe dev-openjobseu \
    --project dev-openjobseu \
    --region europe-north1 \
    --format='value(status.url)' || true)"
  if [ -n "${GCLOUD_URL:-}" ]; then
    append_candidate "${GCLOUD_URL}"
  fi
fi

append_candidate "$FIXED_CLOUD_RUN_URL"
append_candidate "$LOCAL_URL"

for base_url in $CANDIDATES; do
  if curl -fsS -X POST "${base_url}/internal/tick"; then
    exit 0
  fi
done

echo "tick-dev.sh: all tick endpoints failed:${CANDIDATES}" >&2
exit 1
