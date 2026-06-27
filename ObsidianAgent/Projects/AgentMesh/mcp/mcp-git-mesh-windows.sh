#!/usr/bin/env bash
# AgentMesh shared MCP — git, scoped to the live AOPS Git workspace.
# Windows-compatible version with WSL path adaptation.
set -euo pipefail
MCP_GIT="$(which mcp-server-git 2>/dev/null || echo "")"
REPO="${MESH_GIT_REPO:-/mnt/c/Users/AOPSec/Desktop/Git}"
[ -n "$MCP_GIT" ] || { echo "[ERROR] git MCP not found: mcp-server-git (install via: pipx install mcp-server-git)" >&2; exit 127; }
[ -d "$REPO/.git" ] || { echo "[ERROR] not a git repo: $REPO" >&2; exit 2; }
exec "$MCP_GIT" --repository "$REPO" "$@"
