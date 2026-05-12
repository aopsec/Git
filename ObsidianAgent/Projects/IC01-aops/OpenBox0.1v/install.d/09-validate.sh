#!/usr/bin/env bash
# install.d/09-validate.sh — validacao final
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"

# [FIX-V7] Shared helpers sourced from _lib.sh.
# shellcheck source=install.d/_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

run bash "${OPENBOX_ROOT}/tests/validate-stack.sh"
echo "[09-validate] Para report completo: sudo lynis audit system"
