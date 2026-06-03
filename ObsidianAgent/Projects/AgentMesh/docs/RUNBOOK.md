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
`*.bak-pre-mesh`. Done: OpenCode, **OpenHands**. Pending by choice/limitation:
- **OpenHands** (`~/.openhands/config.toml`): DONE & end-to-end verified —
  `base_url=http://host.docker.internal:4000/v1`, `model=openai/qwen2.5-coder`, scoped vkey;
  reachability via the gateway's `172.17.0.1:4000` docker-bridge bind. Also required (all done):
  (a) `[sandbox] runtime_container_image=docker.openhands.dev/openhands/runtime:1.6-nikolaik`
  (OpenHands was failing to *build* a runtime; this pulls the prebuilt one);
  (b) **ADV7ia** `deploy/openhands/compose.yaml` `SANDBOX_RUNTIME_BINDING_ADDRESS=172.17.0.1`
  (was `127.0.0.1` → app couldn't reach the runtime; bound to docker0, not the physical NIC);
  (c) `[mcp] sse_servers=[]` (the `:8101-3` SuperGateway endpoints are down → ~30s timeout/run;
  restore when the bridge is up). Verified: headless run drives `qwen2.5-coder` on the GPU
  (6 `200 OK /chat/completions`/run). Run quality is bounded by the 7B model's CodeAct ability.
- **Cline**: set provider = OpenAI-compatible, base URL = gateway, key = virtual key, in the
  Cline settings UI.
- **HermesAgent**: intentionally left on its own air-gapped ollama.

## Remote access (Tailscale) — RECOMMENDED
Tailnet host: `blk7rch` / `100.109.241.110` / `blk7rch.taile9fb66.ts.net`.
1. **One-time (admin console):** enable **HTTPS Certificates / Serve** for the tailnet
   (https://login.tailscale.com/admin/dns → "Enable HTTPS").
2. Expose the gateway over tailnet HTTPS:
   ```bash
   sudo tailscale serve --bg 4000          # → https://blk7rch.taile9fb66.ts.net  ->  127.0.0.1:4000
   tailscale serve status
   ```
3. Remote use: `curl https://blk7rch.taile9fb66.ts.net/v1/models -H "Authorization: Bearer <virtual-key>"`.

> ⚠️ **Do NOT bind the gateway directly on the tailnet IP** (the old interim
> `docker-compose.override.yml` with `"100.109.241.110:4000:4000"`). Docker cannot bind a
> port to an address that does not yet exist, so if `mesh-litellm` (re)starts while
> `tailscaled` is down or hasn't assigned the `100.x` address — e.g. on reboot, when Docker
> starts before Tailscale — the bind fails with *"cannot assign requested address"* and the
> container **exits 128 and stays down, taking loopback access with it** (one container binds
> both addresses). This took the whole gateway offline on 2026-06-03. The override is retired
> (`gateway/docker-compose.override.yml.bak`); the gateway binds `127.0.0.1:4000` only, which
> always exists. Use `tailscale serve` (above) for remote — it runs inside `tailscaled` and
> forwards to `127.0.0.1:4000`, so it can never block litellm's startup. Scope which devices
> may reach it with **tailnet ACLs**.

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
