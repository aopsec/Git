#!/usr/bin/env bash
# tests/vm/cleanup.sh — remove VM artifacts (disk image + OVMF vars copy)
# The OVMF_VARS copy will be reset on next setup.sh run.
# Pass --all to also remove the artifacts/ directory itself.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACTS="${SCRIPT_DIR}/artifacts"

ALL=false
[[ "${1:-}" == "--all" ]] && ALL=true

if [[ ! -d "$ARTIFACTS" ]]; then
  echo "[OK] Nothing to clean (artifacts/ does not exist)."
  exit 0
fi

rm -f "${ARTIFACTS}/test-disk.qcow2"  && echo "[OK] Removed test-disk.qcow2"
rm -f "${ARTIFACTS}/OVMF_VARS.fd"     && echo "[OK] Removed OVMF_VARS.fd"

if [[ "$ALL" == "true" ]]; then
  rmdir --ignore-fail-on-non-empty "$ARTIFACTS" && echo "[OK] Removed artifacts/"
fi

echo "Done. Run ./setup.sh to recreate."
