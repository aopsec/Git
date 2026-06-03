#!/usr/bin/env bash
# Expose the shared stdio MCP servers to the OpenHands container as SSE, via SuperGateway.
# OpenHands runs in Docker and can't launch host stdio servers, so we bridge stdio->SSE and
# point OpenHands' [mcp] sse_servers at host.docker.internal:<port>.
#
# !! SECURITY !!  SuperGateway has no --host flag, so it binds 0.0.0.0. The fs/git MCP grant
# file/repo access — you MUST restrict ports 8101-8103 to the Docker bridge before use
# (nft rule in docs/HARDENING.md). Prefer running this as a systemd --user service
# (supergateway.service.example) AFTER applying that firewall rule.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

bridge() {  # name port wrapper
  echo "[supergateway] $1 -> :$2 ($3)"
  npx -y supergateway --stdio "$HERE/$3" --port "$2" \
    --healthEndpoint /healthz --logLevel info >"$HERE/.sg-$1.log" 2>&1 &
}

bridge fs    8101 mcp-fs-mesh.sh
bridge git   8102 mcp-git-mesh.sh
bridge vault 8103 mcp-vault-mesh.sh

echo "[supergateway] fs=8101 git=8102 vault=8103 — SSE at /sse, health /healthz"
echo "[supergateway] OpenHands reaches these at http://host.docker.internal:<port>/sse"
wait
