# AgentMesh — Runbook

## Bring up / down the gateway
```bash
cd gateway
cp .env.example .env            # set LITELLM_MASTER_KEY + POSTGRES_PASSWORD (strong)
docker compose up -d
docker exec mesh-ollama ollama pull hermes3:8b
docker exec mesh-ollama ollama pull qwen2.5-coder:7b
docker compose down            # stop (Postgres + model volumes persist)
```
Health: `curl 127.0.0.1:4000/health/liveliness` → `"I'm alive!"`.
Models: `curl 127.0.0.1:4000/v1/models -H "Authorization: Bearer $LITELLM_MASTER_KEY"`.

## Mint a per-user virtual key (multi-tenant)
```bash
bash gateway/mint-key.sh <alias> [budget_usd] [duration]   # e.g. mint-key.sh alice 10 30d
# or directly:
curl -s 127.0.0.1:4000/key/generate -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"key_alias":"alice","models":["qwen2.5-coder","hermes3"],"max_budget":10,"budget_duration":"30d"}'
```
Give each person their `sk-...` virtual key; the master key never leaves `gateway/.env`.

## Point an agent at the gateway
Set the agent's OpenAI-compatible **base_url** = `http://127.0.0.1:4000/v1`, **api_key** = a
virtual key, **model** = `qwen2.5-coder` (or `hermes3`). Backups were saved as
`*.bak-pre-mesh`. Done: OpenCode. Pending by choice/limitation:
- **OpenHands** (`~/.openhands/config.toml`): `base_url=http://host.docker.internal:4000/v1`,
  `model=openai/qwen2.5-coder` — needs a host→container route for `:4000` (replicate the
  existing `:1234` bridge proxy) before it works.
- **Cline**: set provider = OpenAI-compatible, base URL = gateway, key = virtual key, in the
  Cline settings UI.
- **HermesAgent**: intentionally left on its own air-gapped ollama.

## Remote access (Tailscale) — RECOMMENDED
Tailnet host: `blk7rch` / `100.109.241.110` / `blk7rch.tail66a94.ts.net`.
1. **One-time (admin console):** enable **HTTPS Certificates / Serve** for the tailnet
   (https://login.tailscale.com/admin/dns → "Enable HTTPS").
2. Expose the gateway over tailnet HTTPS:
   ```bash
   sudo tailscale serve --bg 4000          # → https://blk7rch.tail66a94.ts.net  ->  127.0.0.1:4000
   tailscale serve status
   ```
3. Remote use: `curl https://blk7rch.tail66a94.ts.net/v1/models -H "Authorization: Bearer <virtual-key>"`.

**Interim (no admin toggle needed):** bind the gateway on the tailnet IP — add
`"100.109.241.110:4000:4000"` to the `litellm` `ports:` in `gateway/docker-compose.yml`,
`docker compose up -d`. Reachable by tailnet members over WireGuard-encrypted HTTP; still
gated by virtual keys. Scope which devices may reach it with **tailnet ACLs**.

## Egress allowlist (only if cloud is enabled later — Phase 2)
Add provider keys to `gateway/.env`, add cloud `model_list` entries + fallbacks to
`gateway/litellm-config.yaml`, and route cloud egress through a Squid allowlist (reuse the
HermesAgent `squid/` pattern) limited to the provider API hosts.

## Retire LM Studio (only when the mesh is fully proven — destructive, sudo)
```bash
sudo systemctl disable --now lmstudio-docker-proxy.service   # + any LM Studio launcher
# then remove LM Studio; agents already use the gateway.
```

## OpenHands MCP via SuperGateway
The shared stdio servers are bridged to SSE for the OpenHands container; `config.toml`
`[mcp] sse_servers` is already wired to `host.docker.internal:8101/8102/8103`. To activate:
1. **Firewall first** — SuperGateway binds `0.0.0.0` and fs/git MCP are sensitive; restrict
   the ports to the Docker bridge (nft rule in `docs/HARDENING.md`).
2. Start the bridge: `bash mcp/supergateway-up.sh` (or install `mcp/supergateway.service.example`
   as a `systemd --user` service). Verify: `curl http://127.0.0.1:8101/healthz` → `ok`.
3. Restart OpenHands (`~/bin/restart-openhands-local`) so it loads the SSE servers.
4. `~/.openhands/settings.json` is root-owned (written by the container) and may take
   precedence over `config.toml`; if OpenHands doesn't show the tools, add the three
   `http://host.docker.internal:<port>/sse` servers via the OpenHands **MCP settings UI**.

## Cline MCP
Add the same `mcp/*.sh` servers via Cline's MCP settings UI in VS Code (extension state).
