#!/usr/bin/env bash
# AgentMesh shared MCP — git, scoped to the live AOPS Git workspace.
# Reuses the already-installed mcp_server_git venv (no network).
set -euo pipefail
PY="$HOME/.local/mcp-servers/git/.venv/bin/python"
REPO="${MESH_GIT_REPO:-/home/aops/OPia/Git}"
[ -x "$PY" ] || { echo "[ERROR] git MCP python not found: $PY" >&2; exit 127; }
[ -d "$REPO/.git" ] || { echo "[ERROR] not a git repo: $REPO" >&2; exit 2; }
exec "$PY" -m mcp_server_git --repository "$REPO" "$@"
