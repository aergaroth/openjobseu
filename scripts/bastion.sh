#!/usr/bin/env bash
set -euo pipefail

INSTANCE_NAME="${BASTION_INSTANCE_NAME:-openjobseu-audit-bastion}"
ZONE="${BASTION_ZONE:-europe-north1-a}"
LOCAL_PORT="${BASTION_LOCAL_PORT:-8888}"
REMOTE_PORT="${BASTION_REMOTE_PORT:-8888}"

require_gcloud() {
  if ! command -v gcloud >/dev/null 2>&1; then
    echo "Missing required command: gcloud" >&2
    exit 1
  fi
}

get_status() {
  gcloud compute instances describe "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --format="value(status)"
}

wait_for_status() {
  local expected="$1"
  local attempts="${2:-24}"
  local delay_seconds="${3:-5}"
  local current=""

  for ((i=1; i<=attempts; i++)); do
    current="$(get_status)"
    if [[ "$current" == "$expected" ]]; then
      echo "$current"
      return 0
    fi
    sleep "$delay_seconds"
  done

  echo "$current"
  return 1
}

print_state() {
  local status="$1"
  echo "Bastion: $INSTANCE_NAME"
  echo "Zone: $ZONE"
  echo "Status: $status"
  echo "Tunnel URL: http://localhost:${LOCAL_PORT}/internal/audit"
}

open_tunnel() {
  echo "Opening IAP tunnel on localhost:${LOCAL_PORT} ..."
  echo "Close it with Ctrl+C when you're done."
  gcloud compute ssh "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --tunnel-through-iap \
    -- -L "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" -N
}

do_up() {
  local status="$1"

  case "$status" in
    RUNNING)
      echo "Bastion is already running."
      ;;
    TERMINATED|STOPPING)
      if [[ "$status" == "STOPPING" ]]; then
        echo "Bastion is stopping. Waiting for TERMINATED before restart ..."
        wait_for_status "TERMINATED" 24 5 >/dev/null
      fi
      echo "Starting bastion ..."
      gcloud compute instances start "$INSTANCE_NAME" --zone="$ZONE"
      echo "Waiting for RUNNING ..."
      wait_for_status "RUNNING" 24 5 >/dev/null
      ;;
    PROVISIONING|STAGING)
      echo "Bastion is still booting. Waiting for RUNNING ..."
      wait_for_status "RUNNING" 24 5 >/dev/null
      ;;
    *)
      echo "Unsupported bastion state for 'up': $status" >&2
      exit 1
      ;;
  esac

  echo "Bastion is ready."
  echo "Open in browser: http://localhost:${LOCAL_PORT}/internal/audit"
  open_tunnel
}

do_down() {
  local status="$1"

  case "$status" in
    TERMINATED)
      echo "Bastion is already stopped."
      ;;
    STOPPING)
      echo "Bastion is already stopping."
      ;;
    *)
      echo "Stopping bastion ..."
      gcloud compute instances stop "$INSTANCE_NAME" --zone="$ZONE"
      ;;
  esac
}

prompt_action() {
  local status="$1"
  local action=""

  print_state "$status"
  echo
  echo "Available actions:"
  echo "  up   - start bastion if needed and open the IAP tunnel"
  echo "  down - stop bastion"
  echo "  q    - quit"
  printf "Choose action [up/down/q]: "
  read -r action
  echo "$action"
}

main() {
  require_gcloud

  local status
  status="$(get_status)"

  local action="${1:-}"
  if [[ -z "$action" ]]; then
    action="$(prompt_action "$status")"
  fi

  case "$action" in
    up)
      do_up "$status"
      ;;
    down)
      do_down "$status"
      ;;
    q|quit|exit)
      print_state "$status"
      ;;
    *)
      echo "Unknown action: $action" >&2
      echo "Usage: $0 [up|down]" >&2
      exit 1
      ;;
  esac
}

main "$@"
