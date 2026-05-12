# ADV7ia Control Mesh Runbook

**Goal:** orchestrate the local AI stack with a recursive feedback chain, Obsidian meta-vault memory, and a security-first network boundary.

## Architecture

```text
LAN Browser
    |
    v
Caddy mTLS Proxy adv7ia-control.home.arpa:8443
    |
    v
OpenHands UI 127.0.0.1:3000
    |
    +--> OpenHands bridge proxy 172.17.0.1:3000
    |
    +--> LM Studio 127.0.0.1:1234/v1
    +--> Qdrant 127.0.0.1:6333
    +--> Repo-scoped MCP tools
    |
    v
ADV7ia Control Mesh
    |
    +--> Planner
    +--> Executor
    +--> Security Reviewer
    +--> Memory Curator
    +--> Session Manager
    |
    v
Obsidian Meta-Vault (`vault/Operations`)
```

## Control Loop

1. Intake: record the task in `state/tasks/`.
2. Plan: assign a role and set recursion, retry, and token budgets.
3. Execute: run a bounded worker session against repo-scoped tools only.
4. Verify: checkpoint outputs, artifacts, and blockers.
5. Summarize: persist the result into Obsidian and Qdrant-friendly artifacts.
6. Requeue or close: branch only while depth and retry caps remain within policy.

## Token Renewal

- `80%`: warn and stop attaching low-value context.
- `90%`: freeze new branches for the current session.
- `95%`: compact automatically into a new session and write a note under `vault/Operations/Compactions/`.

Run:

```bash
bash tools/control-mesh status
bash tools/control-mesh reconcile --plan
bash tools/control-mesh reconcile --apply
bash tools/bootstrap-adv7ia-rag
bash tools/control-mesh compact --session-id session-bootstrap-openhands --force
```

`reconcile --apply` uses the OpenHands settings API when
`ADV7IA_OPENHANDS_SETTINGS_API_URL` is available. Otherwise it patches the local
`~/.openhands/settings.json` file and recreates immutable Docker drift through
`docker compose up -d --force-recreate --wait`.

## Security Invariants

- OpenHands listens on `127.0.0.1:3000` only.
- Docker bridge sandboxes reach OpenHands through `172.17.0.1:3000`, proxied back to `127.0.0.1:3000`.
- LAN access goes through `deploy/caddy/Caddyfile` with mutual TLS on `https://adv7ia-control.home.arpa:8443`.
- `USE_HOST_NETWORK=false`
- `privileged=false`
- risky actions stay gated even when recursion and compaction are automatic

## Proxy Ownership

- The active bridge-proxy deployment target is `deploy/systemd-user/openhands-docker-proxy.service`.
- `deploy/systemd/openhands-docker-proxy.service` is intentionally retained as the later
  system-scope cutover target.
- The preferred Caddy deployment target is the host `caddy.service`, but the repo also
  provides `deploy/systemd-user/adv7ia-caddy-lan-proxy.service` for rootless installs.
- Rootless Caddy installs use the official static `caddy` binary under
  `${HOME}/.local/bin/caddy` and store the generated server CA, client CA, and sample
  client certificate under `${HOME}/.local/share/adv7ia/caddy/`.
- The `vmtst` GNOME Boxes guest can keep a persistent reverse tunnel back to the host by
  installing `deploy/systemd-guest/adv7ia-vmtst-reverse-tunnel.service` with
  `deploy/bin/install-vmtst-reverse-tunnel`. That gives the host a stable
  `127.0.0.1:2222 -> vmtst:22` path without relying on temporary QEMU monitor forwards.
- Audits accept either scope today, but the current baseline expects the user-scoped proxy
  to remain active until a deliberate migration is scheduled.

Audit:

```bash
bash tools/audit-control-mesh
bash tools/audit-control-mesh --live
```

## Obsidian Notes

- `vault/Operations/Task Queue.md`
- `vault/Operations/Session Ledger.md`
- `vault/Operations/Security Policy.md`
- `vault/Operations/Incident Review.md`
- `vault/Operations/Compactions/README.md`
