#!/usr/bin/env bash
#
# Triggers a full synchronization (ingestion) of all registered ATS companies 
# by overriding the incremental fetch limit. It calculates the necessary 
# number of batches and safely handles potential Cloud Run timeouts.
#

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

TARGET_URL=""
AUTH_HEADER=""

if command -v gcloud >/dev/null 2>&1; then
  TOKEN=$(gcloud auth print-identity-token 2>/dev/null || true)
  if [ -n "$TOKEN" ]; then
    AUTH_HEADER="Authorization: Bearer $TOKEN"
  fi
fi

for base_url in $CANDIDATES; do
  ready_status="$(curl -sS -H "$AUTH_HEADER" -o /dev/null -w "%{http_code}" "${base_url}/ready" || true)"
  
  if [ "${ready_status:-000}" = "200" ]; then
    TARGET_URL="$base_url"
    break
  fi
done

if [ -z "$TARGET_URL" ]; then
  echo "tick-full-sync.sh: Nie znaleziono żadnego działającego endpointu /ready w kandydatach: ${CANDIDATES}" >&2
  exit 1
fi

# 1. Pobierz liczbę firm z ATS
METRICS_JSON=$(curl -sS -H "$AUTH_HEADER" "${TARGET_URL}/internal/metrics")
TOTAL_ATS=$(echo "$METRICS_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('company_ats_total', 0))" 2>/dev/null || echo "0")

if [ "$TOTAL_ATS" -eq 0 ]; then
  echo "Nie znaleziono integracji ATS (lub wystąpił błąd parsowania /internal/metrics)."
  exit 0
fi

LIMIT=5
ITERS=$(( (TOTAL_ATS + LIMIT - 1) / LIMIT ))
MAX_RETRIES=3

echo "Docelowy URL: $TARGET_URL"
echo "Rozpoczynam pełną synchronizację (Full Fetch) dla $TOTAL_ATS firm w $ITERS iteracjach (limit=$LIMIT na żądanie)."

for ((i=1; i<=ITERS; i++)); do
  # 1. Rysowanie paska postępu
  WIDTH=40
  PERCENT=$(( i * 100 / ITERS ))
  FILLED=$(( i * WIDTH / ITERS ))
  EMPTY=$(( WIDTH - FILLED ))
  BAR=""
  for ((j=0; j<FILLED; j++)); do BAR="${BAR}#"; done
  for ((j=0; j<EMPTY; j++)); do BAR="${BAR}-"; done

  echo -e "\n[${BAR}] ${PERCENT}% (Iteracja ${i}/${ITERS})"

  # 2. Bezpieczne żądanie z mechanizmem Retry (np. na wypadek HTTP 502 / 504 z Cloud Run)
  ATTEMPT=1
  SUCCESS=0

  while [ $ATTEMPT -le $MAX_RETRIES ]; do
    TMP_BODY="$(mktemp)"
    # Zapisujemy odpowiedź do pliku, a status HTTP do zmiennej. 
    # Konstrukcja '|| echo "000"' ratuje skrypt przed przerwaniem przez 'set -e' w razie zerwania TCP.
    HTTP_CODE=$(curl -sS -w "%{http_code}" -X POST -H "$AUTH_HEADER" -o "$TMP_BODY" \
         "${TARGET_URL}/internal/tick?incremental=false&limit=${LIMIT}&group=ingestion&format=text" || echo "000")

    if [ "$HTTP_CODE" = "200" ]; then
      cat "$TMP_BODY"
      rm -f "$TMP_BODY"
      SUCCESS=1
      break
    else
      echo -e "\n[!] Wystąpił błąd komunikacji (HTTP $HTTP_CODE). Próba $ATTEMPT z $MAX_RETRIES za 5 sekund..."
      cat "$TMP_BODY" 2>/dev/null || true
      rm -f "$TMP_BODY"
      sleep 5
      ATTEMPT=$((ATTEMPT + 1))
    fi
  done

  if [ $SUCCESS -eq 0 ]; then
    echo -e "\n[!] Zbyt wiele błędów połączenia. Przerwano pełną synchronizację na iteracji $i."
    exit 1
  fi

  sleep 2 # Lekki oddech dla bazy danych między pomyślnymi żądaniami
done

echo -e "\nZakończono pełną synchronizację!"