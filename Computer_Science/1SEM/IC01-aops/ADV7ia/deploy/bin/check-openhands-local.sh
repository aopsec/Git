#!/usr/bin/env bash
# [FIX-OH-07] Validate the split OpenHands routing model for host and Docker bridge clients.
set -euo pipefail
shopt -s inherit_errexit

cleanup() {
  :
}

print_service_state() {
  local service_name="$1"

  if systemctl is-active --quiet "${service_name}"; then
    printf 'active (system)\n'
    return 0
  fi
  if systemctl --user is-active --quiet "${service_name}"; then
    printf 'active (user)\n'
    return 0
  fi
  systemctl is-active "${service_name}" 2>/dev/null || systemctl --user is-active "${service_name}" 2>/dev/null || true
}

section() {
  local title="$1"
  printf '\n===== %s =====\n' "${title}"
}

probe_openhands_app() {
  local container_name="openhands-app"

  if ! docker ps --format "{{.Names}}" | grep -qx "${container_name}"; then
    echo "OpenHands app container is not running."
    return 0
  fi

  docker exec -i "${container_name}" python3 - <<'PY' || true
import os
import urllib.request

print("HOME:", os.environ.get("HOME"))
print("config:", os.path.exists("/root/.openhands/config.toml"))
print("file_store:", os.path.exists("/.openhands"))

for url in [
    "http://host.docker.internal:3000/health",
    "http://host.docker.internal:1234/v1/models",
]:
    try:
        response = urllib.request.urlopen(url, timeout=10)
        print("OK:", url, response.status)
    except Exception as exc:
        print("FAIL:", url, repr(exc))
PY
}

trap cleanup EXIT INT

section "Docker"
systemctl is-active docker.service || true

section "OpenHands bridge allow"
systemctl is-active openhands-docker-bridge-allow.service || true

section "OpenHands Docker bridge proxy"
print_service_state openhands-docker-proxy.service

section "LM Studio Docker proxy"
systemctl is-active lmstudio-docker-proxy.service || true

section "LM Studio host API"
curl -fsS http://127.0.0.1:1234/v1/models | jq -r '.data[].id' || true

section "LM Studio Docker bridge API"
curl -fsS http://172.17.0.1:1234/v1/models | jq -r '.data[].id' || true

section "OpenHands host health"
curl -fsS http://127.0.0.1:3000/health || true
echo

section "OpenHands Docker bridge health"
curl -fsS http://172.17.0.1:3000/health || true
echo

section "OpenHands app container test"
probe_openhands_app

section "Containers"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep -E 'openhands|oh-agent|NAMES' || true

SANDBOX="$(docker ps -a --filter "name=oh-agent-server" --format "{{.Names}}" | head -n1 || true)"

if [[ -n "${SANDBOX}" ]]; then
  section "Sandbox network test: ${SANDBOX}"
  docker exec -i "${SANDBOX}" python3 - <<'PY' || true
import urllib.request

for url in [
    "http://host.docker.internal:3000/health",
    "http://host.docker.internal:1234/v1/models",
]:
    try:
        response = urllib.request.urlopen(url, timeout=10)
        print("OK:", url, response.status)
    except Exception as exc:
        print("FAIL:", url, repr(exc))
PY
else
  echo
  echo "No oh-agent-server sandbox currently running."
fi
