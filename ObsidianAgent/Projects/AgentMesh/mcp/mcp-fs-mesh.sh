#!/usr/bin/env bash
# AgentMesh shared MCP — filesystem, scoped to the live AOPS Git workspace.
# Reuses the already-installed @modelcontextprotocol/server-filesystem (no network).
set -euo pipefail
ROOT="$HOME/.local/mcp-servers/filesystem"
TARGET="${MESH_FS_TARGET:-/home/aops/OPia/Git}"
BIN="$ROOT/node_modules/.bin/mcp-server-filesystem"
[ -x "$BIN" ] || { echo "[ERROR] filesystem MCP not installed: $BIN" >&2; exit 127; }
exec "$BIN" "$TARGET"
