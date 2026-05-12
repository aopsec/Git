#!/usr/bin/env bash
# /usr/local/sbin/openbox-container-running.sh
# [FIX-AUDIT-MONIT] Exit 0 only when a named Docker container exists and is running.
set -euo pipefail
shopt -s inherit_errexit

readonly CONTAINER_NAME="${1:?container name required}"

if ! command -v docker >/dev/null 2>&1; then
  exit 1
fi

STATE="$(docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
[[ "${STATE}" == "true" ]]
