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
  # 1. Pobierz token (jeśli gcloud jest dostępny)
  AUTH_HEADER=""
  if command -v gcloud >/dev/null 2>&1; then
    TOKEN=$(gcloud auth print-identity-token 2>/dev/null || true)
    if [ -n "$TOKEN" ]; then
      AUTH_HEADER="Authorization: Bearer $TOKEN"
    fi
  fi

  # 2. Sprawdź /ready (dodajemy nagłówek)
  ready_body="$(mktemp)"
  ready_status="$(curl -sS -H "$AUTH_HEADER" -o "$ready_body" -w "%{http_code}" "${base_url}/ready" || true)"
  
  if [ "${ready_status:-000}" != "200" ]; then
    echo "tick-dev.sh: ${base_url}/ready -> ${ready_status:-000}" >&2
    # ... reszta obsługi błędu ...
    continue
  fi
  rm -f "$ready_body"

  # 3. Wykonaj POST /internal/tick (dodajemy nagłówek)
  tick_body="$(mktemp)"
  tick_status="$(curl -sS -X POST -H "$AUTH_HEADER" -o "$tick_body" -w "%{http_code}" "${base_url}/internal/tick?format=text" || true)"
  

  echo "tick-dev.sh: ${base_url}/internal/tick?format=text -> ${tick_status:-000}" >&2
  cat "$tick_body" >&2 || true
  rm -f "$tick_body"
done

echo "tick-dev.sh: all tick endpoints failed:${CANDIDATES}" >&2
exit 1
