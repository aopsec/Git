#!/usr/bin/env bash
# bbWebScan one-command audit gate.
#
# Runs ruff → mypy --strict → pytest -q --cov in order; exits non-zero on the
# first failure. Used as the "fully audited" entry point referenced in
# CLAUDE.md and CHANGELOG.md.
#
# Usage:
#   bash scripts/verify.sh
#
# Skip individual gates via env (CI rarely needs this):
#   VERIFY_SKIP_RUFF=1 VERIFY_SKIP_MYPY=1 bash scripts/verify.sh
set -euo pipefail

cd "$(dirname "$0")/.."

# Resolve a Python interpreter. Prefer the project venv when present; the
# generated console-script wrappers (ruff, mypy, pytest) hard-code absolute
# paths and break if the venv was created at a different location, so we
# invoke each tool via ``python -m`` instead — works regardless of shebang.
if [[ -n "${VIRTUAL_ENV:-}" ]] && [[ -x "$VIRTUAL_ENV/bin/python" ]]; then
    PY="$VIRTUAL_ENV/bin/python"
elif [[ -x .venv/bin/python ]]; then
    PY=".venv/bin/python"
else
    PY="$(command -v python3 || command -v python)"
fi

step() {
    printf '\n=== %s ===\n' "$1"
}

if [[ -z "${VERIFY_SKIP_RUFF:-}" ]]; then
    step "ruff check ."
    "$PY" -m ruff check .
fi

if [[ -z "${VERIFY_SKIP_MYPY:-}" ]]; then
    step "mypy"
    "$PY" -m mypy
fi

if [[ -z "${VERIFY_SKIP_PYTEST:-}" ]]; then
    step "pytest -q --cov"
    "$PY" -m pytest -q --cov
fi

printf '\nverify.sh: all gates passed\n'
