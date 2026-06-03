#!/usr/bin/env bash
# AgentMesh executor MCP launcher (mesh-executors: run_hermes / run_opencode / run_openhands).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/.venv/bin/python"
[ -x "$PY" ] || { echo "[ERROR] executor venv missing: $PY (run: uv venv .venv && uv pip install mcp)" >&2; exit 127; }
exec "$PY" "$HERE/exec_mesh.py"
