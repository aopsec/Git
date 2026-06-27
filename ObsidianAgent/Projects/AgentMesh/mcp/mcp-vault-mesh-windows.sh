#!/usr/bin/env bash
# AgentMesh shared MCP — the ObsidianAgent vault as shared agent memory/knowledge.
# Windows-compatible version with WSL path adaptation.
# NOTE: RW within the vault. Vault/Generated/ is machine-managed (determinism contract);
# agents must NOT write there — `obsidian_agent_cli.py --check` catches any drift.
set -euo pipefail
ROOT="$HOME/.local/mcp-servers/filesystem"
TARGET="${MESH_VAULT_TARGET:-/mnt/c/Users/AOPSec/Desktop/Git/ObsidianAgent/Vault}"
BIN="$ROOT/node_modules/.bin/mcp-server-filesystem"
[ -x "$BIN" ] || { echo "[ERROR] filesystem MCP not installed: $BIN" >&2; exit 127; }
exec "$BIN" "$TARGET"
