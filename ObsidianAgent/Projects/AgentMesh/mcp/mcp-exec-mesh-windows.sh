#!/usr/bin/env bash
# AgentMesh executor MCP launcher (mesh-executors: run_hermes / run_opencode / run_openhands).
# Windows-compatible version.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/.venv/bin/python"
[ -x "$PY" ] || { echo "[ERROR] executor venv missing: $PY (run: python3 -m venv .venv && .venv/bin/pip install mcp fastmcp)" >&2; exit 127; }
exec "$PY" "$HERE/exec_mesh.py"
