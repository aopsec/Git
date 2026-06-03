# AgentMesh — User Guide

A complete, task-oriented walkthrough for running and using AgentMesh correctly: from a cold
box to driving every executor, sharing tools over MCP, and reaching the mesh from another
device. Commands here are verified against this host (`blk7rch`, Arch + RTX 4070 Ti).

**How this fits the other docs**
- **This guide** — *how to use it*, step by step, with troubleshooting.
- [`README.md`](../README.md) — one-page overview (pt-br).
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — *how it's built* (topology, layers, decisions).
- [`docs/RUNBOOK.md`](RUNBOOK.md) — terse ops cheat-sheet (start/stop, keys, remote).
- [`docs/HARDENING.md`](HARDENING.md) — threat model, controls, residual risks.
- [`CLAUDE.md`](../CLAUDE.md) — engineering conventions for changing the project.

---

## Contents
1. [Mental model](#1-mental-model)
2. [Prerequisites](#2-prerequisites)
3. [First-time setup](#3-first-time-setup-one-time)
4. [Daily operation](#4-daily-operation)
5. [Using the gateway directly](#5-using-the-gateway-directly)
6. [Virtual keys (per-user access)](#6-virtual-keys-per-user-access)
7. [Pointing your agents at the gateway](#7-pointing-your-agents-at-the-gateway)
8. [Shared MCP tools (fs / git / vault)](#8-shared-mcp-tools-fs--git--vault)
9. [Executor dispatch (run_hermes / run_opencode / run_openhands)](#9-executor-dispatch)
10. [Remote access over Tailscale](#10-remote-access-over-tailscale)
11. [Common workflows](#11-common-workflows)
12. [Verification checklist](#12-verification-checklist)
13. [Troubleshooting](#13-troubleshooting)
14. [Security: do's & don'ts](#14-security-dos--donts)
15. [Reference appendix](#15-reference-appendix)

---

## 1. Mental model

AgentMesh turns a pile of separate AI tools into one mesh with three ideas:

- **One door (the gateway).** Every agent talks to a single OpenAI-compatible endpoint,
  `http://127.0.0.1:4000`. LiteLLM sits there and routes to a **local GPU model** (`hermes3`
  or `qwen2.5-coder` on Ollama). No cloud by default.
- **Shared tools (MCP).** All planners see the same tools: project **files**, **git**, and the
  Obsidian **vault** (shared memory) — plus **exec-mesh**, which lets one agent call another.
- **Planners vs executors.** *Planners* (Claude, Copilot) decide and dispatch; *executors*
  (Hermes, OpenCode, OpenHands) do the work. MCP is the glue.

```
  Claude / Copilot (planners)
        │  MCP
        ▼
  fs-mesh · git-mesh · vault-mesh · exec-mesh ──► run_hermes / run_opencode / run_openhands
        │                                                     │
        │ OpenAI API (127.0.0.1:4000)                         │ dispatch
        ▼                                                     ▼
  LiteLLM gateway ── mesh-ollama (GPU) ── hermes3 · qwen2.5-coder
        ▲
  Remote devices ── Tailscale (encrypted) + per-user virtual key
```

Two Ollamas exist on purpose: **HermesAgent keeps its own air-gapped ollama**; the mesh runs a
separate **mesh-ollama** the gateway can reach. They share the 12 GB GPU (loaded on demand).

---

## 2. Prerequisites

| Need | Why | Check |
|---|---|---|
| Docker + compose v2 | runs every service | `docker version`, `docker compose version` |
| NVIDIA driver + `nvidia-container-toolkit` + CDI | GPU passthrough to Ollama | `nvidia-smi`; `/etc/cdi/nvidia.yaml` exists |
| The repo checkout | configs + wrappers | `/home/aops/OPia/Git/ObsidianAgent/Projects/AgentMesh` |
| (Remote) Tailscale | reach the mesh off-box | `tailscale status` |
| (MCP) installed MCP servers | shared tools | `~/.local/mcp-servers/{filesystem,git}` |

> GPU/CDI setup is shared with HermesAgent — see `HermesAgent/setup.sh gpu` if `nvidia-smi`
> works on the host but not inside a container.

---

## 3. First-time setup (one-time)

```bash
cd /home/aops/OPia/Git/ObsidianAgent/Projects/AgentMesh/gateway

# 1) Secrets: copy the template and set STRONG values for both.
cp .env.example .env
#    LITELLM_MASTER_KEY=sk-mesh-master-<long-random>   (admin key — never give to clients)
#    POSTGRES_PASSWORD=<strong-random>
chmod 600 .env

# 2) Bring up gateway + Postgres + mesh-ollama.
docker compose up -d

# 3) Pull the local models into mesh-ollama (one time; cached in a volume).
docker exec mesh-ollama ollama pull hermes3:8b
docker exec mesh-ollama ollama pull qwen2.5-coder:7b

# 4) Smoke test (expects the model list with the master key).
MK=$(grep '^LITELLM_MASTER_KEY=' .env | cut -d= -f2-)
curl -s 127.0.0.1:4000/v1/models -H "Authorization: Bearer $MK"
```

You should see `hermes3`, `qwen2.5-coder`, and the `qwen3-coder-local` alias.

> **The gateway binds `127.0.0.1:4000` (host) and `172.17.0.1:4000` (docker bridge).** The
> bridge bind lets *other containers* (e.g. OpenHands) reach it via `host.docker.internal`.
> Remote devices use Tailscale (§10) — **never** add a bind to a tailnet/LAN IP directly
> (see [Troubleshooting → gateway won't start](#gw-bind)).

---

## 4. Daily operation

```bash
cd .../AgentMesh/gateway

docker compose up -d        # start (idempotent)
docker compose ps           # what's running
docker compose logs -f litellm   # follow gateway logs
docker compose down         # stop (Postgres + model volumes persist)
```

**Status at a glance:**
```bash
docker ps --format '{{.Names}}\t{{.Status}}' | grep -E 'mesh-|hermes|openhands'
docker port mesh-litellm                       # expect 127.0.0.1:4000 AND 172.17.0.1:4000
curl -s 127.0.0.1:4000/health/liveliness       # → "I'm alive!"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
```

Order doesn't matter for local use. For **remote** use, `tailscaled` must be up (§10) — but the
gateway no longer depends on it, so a Tailscale outage never takes local access down.

---

## 5. Using the gateway directly

It's a standard OpenAI-compatible API. Auth is **required** (a virtual key or, for admin, the
master key). Use a **virtual key** for everyday calls (§6), not the master key.

```bash
KEY=sk-...   # a virtual key

# List models
curl -s 127.0.0.1:4000/v1/models -H "Authorization: Bearer $KEY"

# Chat completion (routes to the GPU)
curl -s 127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5-coder","messages":[{"role":"user","content":"Reply with: PONG"}]}'
```

- `model`: `qwen2.5-coder` (coding) or `hermes3` (general). `qwen3-coder-local` is a back-compat
  alias → `qwen2.5-coder`.
- No key → **401** (by design). Wrong host/port → connection error.

---

## 6. Virtual keys (per-user access)

Each person/agent gets a **scoped, budgeted** key. The master key stays in `gateway/.env` and is
used only to mint/manage keys.

```bash
# Mint:  alias  budget_usd  duration
bash gateway/mint-key.sh alice 10 30d
# → alias=alice key=sk-...  budget=10/30d   (hand the sk-... to that user)
```

The minted key is **scoped to `qwen2.5-coder` + `hermes3`** with a budget. Manage keys via the
master key:

```bash
MK=$(grep '^LITELLM_MASTER_KEY=' gateway/.env | cut -d= -f2-)

# List
curl -s 127.0.0.1:4000/key/info -H "Authorization: Bearer $MK"
# Revoke
curl -s 127.0.0.1:4000/key/delete -H "Authorization: Bearer $MK" \
  -H 'Content-Type: application/json' -d '{"keys":["sk-..."]}'
```

> Keys/budgets/audit live in Postgres (`mesh-pg` volume). **Back it up before tearing the stack
> down** if you want keys to survive.

---

## 7. Pointing your agents at the gateway

Set each agent's OpenAI-compatible **base_url**, **api_key** (a virtual key), and **model**.

| Agent | Where | base_url | model |
|---|---|---|---|
| **OpenCode** | `~/.config/opencode/opencode.json` | `http://127.0.0.1:4000/v1` | `qwen2.5-coder` |
| **OpenHands** | `~/.openhands/config.toml` `[llm]` | `http://host.docker.internal:4000/v1` | `openai/qwen2.5-coder` |
| **Cline** | VS Code UI (provider = OpenAI-compatible) | `http://127.0.0.1:4000/v1` | `qwen2.5-coder` |
| **Claude / Copilot** | planners — consume MCP (§8); LLM is the cloud Claude | — | — |
| **HermesAgent** | *intentionally left on its own air-gapped ollama* | — | — |

Notes:
- **Containers** (OpenHands) must use `host.docker.internal:4000` (→ the `172.17.0.1` bridge
  bind), not `127.0.0.1`. The `openai/` prefix routes via the OpenAI-compatible path.
- OpenHands also needs `[sandbox] runtime_container_image` set to the prebuilt runtime and the
  ADV7ia compose `SANDBOX_RUNTIME_BINDING_ADDRESS=172.17.0.1` — both already configured; see
  §13 if you rebuild that deployment.
- After editing `~/.openhands/config.toml` (a single-file bind mount), **recreate** the
  container — an in-place rewrite leaves the old config bound:
  ```bash
  OH_PROJECT_ROOT=/home/aops/OPia/Git/ObsidianAgent/Projects/ADV7ia ~/bin/restart-openhands-local
  ```

---

## 8. Shared MCP tools (fs / git / vault)

Planners (Claude/Copilot) get four MCP servers, registered in `/home/aops/OPia/Git/.mcp.json`
and launched by the wrappers in `mcp/`:

| Server | Exposes | Scope |
|---|---|---|
| `fs-mesh` | filesystem | `/home/aops/OPia/Git` (the repo) |
| `git-mesh` | git ops | the repo |
| `vault-mesh` | filesystem | the Obsidian vault (`ObsidianAgent/Vault`) — shared memory |
| `exec-mesh` | executor dispatch | `run_hermes` / `run_opencode` / `run_openhands` (§9) |

```bash
claude mcp list     # expect fs-mesh, git-mesh, vault-mesh, exec-mesh → Connected
```

Then just ask the planner naturally — e.g. *"read `bbwebscan/cli.py` and summarise"* (fs-mesh),
*"what changed on this branch?"* (git-mesh), *"save this finding to the vault"* (vault-mesh).

> **Vault rule:** agents may read/write the vault, but **never** `Vault/Generated/` (machine-
> managed; drift is caught by `obsidian_agent_cli.py --check`).
>
> The wrappers are repo-pinned with absolute paths (single-box). Override targets with
> `MESH_FS_TARGET` / `MESH_GIT_REPO` / `MESH_VAULT_TARGET` if needed.

---

## 9. Executor dispatch

`exec-mesh` exposes three tools (`run_hermes` / `run_opencode` / `run_openhands`) so a planner can hand a sub-task to an executor. Each shells a
fixed argv (no shell string) with a timeout.

| Tool | Runs | Backend | Timeout |
|---|---|---|---|
| `run_hermes(prompt)` | `docker exec hermes hermes -z <prompt>` | Hermes' **own** air-gapped ollama (`hermes3:8b`) | 300s |
| `run_opencode(prompt, cwd)` | `opencode run <prompt>` in `cwd` | gateway `qwen2.5-coder` | 600s |
| `run_openhands(prompt)` | headless `openhands.core.main -t <prompt>` (`-i 30`) | gateway `qwen2.5-coder` | 900s |

From a planner you simply say *"use run_opencode to add a docstring to foo()"*. To exercise the
underlying paths directly:

```bash
docker exec hermes hermes -z "Reply with: PONG"
opencode run "list the files in this dir"
docker exec openhands-app python -m openhands.core.main --config-file /app/config.toml -i 30 -t "..."
```

> **Reloading the tool:** the `exec-mesh` MCP server is spawned when the planner starts. If you
> edit `exec_mesh.py`, restart the planner (e.g. relaunch Claude Code) to pick up the change.
>
> **OpenHands run quality** is bounded by the 7B model's agent ability — fine for scoped tasks,
> weaker on long multi-step ones. Use `run_hermes` or a larger model for harder jobs.

---

## 10. Remote access over Tailscale

Reach the gateway from another device over the encrypted tailnet — **no public ports**, still
gated by a virtual key. Preferred method: `tailscale serve` (TLS), which forwards into the
loopback gateway, so it can never block the gateway's startup.

```bash
# One-time on the tailnet admin console: enable HTTPS/Serve
#   https://login.tailscale.com/admin/dns  → "Enable HTTPS"   (already enabled for this tailnet)

sudo tailscale up                  # ensure tailscaled is running
sudo tailscale serve --bg 4000     # tailnet HTTPS → 127.0.0.1:4000
tailscale serve status             # shows the https URL → proxy 127.0.0.1:4000
```

This host's tailnet name is **`blk7rch.taile9fb66.ts.net`**. From any tailnet device:

```bash
curl -s https://blk7rch.taile9fb66.ts.net/v1/models -H "Authorization: Bearer <virtual-key>"
# no key → 401
```

- Scope *which* devices may reach it with **tailnet ACLs**.
- **Do not** bind the gateway to the tailnet IP directly — see [Troubleshooting](#gw-bind).

---

## 11. Common workflows

**A. Plan with Claude, execute on a local model**
1. In Claude Code, `claude mcp list` shows `exec-mesh` connected.
2. Ask: *"Refactor `parse()` in `utils.py`; use run_opencode to apply it, then git-mesh to show the diff."*
3. Claude reads via fs-mesh, dispatches to `run_opencode` (GPU), reviews the diff via git-mesh.

**B. One-shot question to the local brain (no agent)**
```bash
KEY=sk-...
curl -s 127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer $KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"hermes3","messages":[{"role":"user","content":"Explain CDI GPU passthrough in 3 lines"}]}'
```

**C. Shared memory across agents**
Have any planner write notes/findings into the vault via `vault-mesh`; another session (or
agent) reads them back later. Keep out of `Vault/Generated/`.

**D. Use the mesh from your laptop**
Point a local OpenAI-compatible client at `https://blk7rch.taile9fb66.ts.net/v1` with your
virtual key (§10).

---

## 12. Verification checklist

Run after setup or any change. All should pass.

```bash
cd .../AgentMesh/gateway; MK=$(grep '^LITELLM_MASTER_KEY=' .env | cut -d= -f2-)

# Gateway up + bound correctly
docker port mesh-litellm                                   # 127.0.0.1:4000 AND 172.17.0.1:4000
curl -s 127.0.0.1:4000/health/liveliness                   # "I'm alive!"

# Auth enforced
curl -s -o /dev/null -w '%{http_code}\n' 127.0.0.1:4000/v1/models          # 401 (no key)
curl -s 127.0.0.1:4000/v1/models -H "Authorization: Bearer $MK" | head     # model list

# GPU routing
curl -s 127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer $MK" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5-coder","messages":[{"role":"user","content":"Reply with: PONG"}],"max_tokens":10}'

# Containers can reach the gateway
docker exec openhands-app curl -s -o /dev/null -w '%{http_code}\n' http://host.docker.internal:4000/health/liveliness  # 200

# MCP + executors
claude mcp list                                            # fs/git/vault/exec → Connected
docker exec hermes hermes -z "Reply with: PONG"            # PONG (run_hermes path)

# Remote (if enabled)
tailscale serve status                                     # https URL → 127.0.0.1:4000
```

The HARDENING "certification gate" (objective 100%) = all the above green **and** meta-vault
`obsidian_agent_cli.py --check` clean.

---

## 13. Troubleshooting

<a id="gw-bind"></a>
**Gateway won't start — `Exited (128)` / "cannot assign requested address".**
A `ports:` entry binds an IP that doesn't exist yet (classically a tailnet IP while `tailscaled`
is down). Docker can't bind a missing address, the container dies, and because one container
binds every address, **loopback dies too**. Fix: the gateway must bind only `127.0.0.1` and
`172.17.0.1` (both always exist); use **`tailscale serve`** for remote (§10), never a direct
tailnet/LAN-IP bind. A retired example lives at `gateway/docker-compose.override.yml.bak`.
Recover: `docker compose up -d`.

**Remote curl returns `000`.** Wrong hostname or `tailscaled` down. The live tailnet name is
`blk7rch.taile9fb66.ts.net` (not any older name). Check `tailscale status` and `tailscale serve
status`.

**`401 Unauthorized`.** Expected with no/invalid key. Pass a valid virtual key; mint one with
`mint-key.sh` (§6).

**A container can't reach the gateway (`connection refused` / exit 7/52).** It's using
`127.0.0.1` (its own loopback) instead of `host.docker.internal:4000`, or the `172.17.0.1:4000`
bridge bind is missing (`docker port mesh-litellm`).

**OpenHands: `Connection refused` to the runtime sandbox.** The runtime port was bound to host
`127.0.0.1`, unreachable from the app. Set `SANDBOX_RUNTIME_BINDING_ADDRESS=172.17.0.1` in
`ADV7ia/deploy/openhands/compose.yaml` and recreate (already configured on this box).

**OpenHands: `docker buildx build ... runtime` fails.** It's trying to *build* a runtime image.
Point it at the prebuilt one: `[sandbox] runtime_container_image =
"docker.openhands.dev/openhands/runtime:1.6-nikolaik"` in `~/.openhands/config.toml`, then
recreate. Pre-pull with `docker pull <that image>` (≈8.5 GB).

**OpenHands: ~30s hangs / `McpError` to `:8101-8103`.** The SuperGateway SSE bridge isn't
running. Keep `[mcp] sse_servers = []` until you stand the bridge up (firewall the ports first —
see HARDENING — then `mcp/supergateway-up.sh`).

**Edited a config but nothing changed.** Single-file bind mounts (`config.toml`,
`cli-config.yaml`) bind the file's inode at container creation; an in-place rewrite is a new
inode. **Recreate** the container, don't just `restart`.

**`restart-openhands-local` → "Project root not found".** The launcher hardcodes
`$HOME/ObsidianAgent`; this checkout is under `OPia/Git/`. Run with
`OH_PROJECT_ROOT=/home/aops/OPia/Git/ObsidianAgent/Projects/ADV7ia ~/bin/restart-openhands-local`.

**MCP tool edit not reflected.** MCP servers launch when the planner starts; restart the planner
(Claude Code / VS Code) to reload `exec_mesh.py` or the wrappers.

**Slow responses / CPU fallback / OOM.** The two Ollamas share 12 GB VRAM. Avoid heavy
concurrent loads on `mesh-ollama` and `hermes-ollama`; check `nvidia-smi`.

---

## 14. Security: do's & don'ts

**Do**
- Keep `gateway/.env` `chmod 600`; treat the **master key** like root — mint **virtual keys**
  for everyone/everything else.
- Keep the gateway/MCP on `127.0.0.1` (+ `172.17.0.1` for containers); expose remotely **only**
  via Tailscale, scoped with ACLs.
- Set budgets + model scope on every virtual key; back up `mesh-pg` before teardown.
- Firewall the SuperGateway ports (8101-8103) to the Docker bridge **before** starting that
  bridge — they grant filesystem/git access.

**Don't**
- Don't put the master key (or cloud keys) into any client/agent config.
- Don't add a `ports:` bind to a tailnet/LAN IP (breaks startup; use `tailscale serve`).
- Don't mount `docker.sock` into an agent you don't trust; don't let agents write
  `Vault/Generated/`.
- Don't assume planners/executors are a security boundary — containment is the container +
  the key gate + the overlay (+ egress allowlist if cloud is ever enabled). See HARDENING.

---

## 15. Reference appendix

**Ports**
| Port | Bind | Service |
|---|---|---|
| 4000 | `127.0.0.1` + `172.17.0.1` | LiteLLM gateway (OpenAI API) |
| 5432 | internal (mesh net) | Postgres (keys/budgets/audit) |
| 11434 | internal | mesh-ollama / hermes-ollama |
| 9119 | `127.0.0.1` | HermesAgent dashboard |
| 3000 | `127.0.0.1` | OpenHands UI |
| 8101-8103 | (bridge, when started) | SuperGateway SSE (fs/git/vault) for OpenHands |

**Models:** `hermes3` (general), `qwen2.5-coder` (coding), `qwen3-coder-local` (alias →
qwen2.5-coder).

**Key files**
| Path | Purpose |
|---|---|
| `gateway/.env` | master key + Postgres password (gitignored, 600) |
| `gateway/litellm-config.yaml` | model routing |
| `gateway/docker-compose.yml` | gateway + Postgres + mesh-ollama; the `127.0.0.1` + `172.17.0.1` binds |
| `gateway/mint-key.sh` | mint a scoped virtual key |
| `mcp/mcp-*.sh`, `mcp/exec_mesh.py` | MCP wrappers + executor dispatch |
| `/home/aops/OPia/Git/.mcp.json` | Claude MCP registration |
| `~/.openhands/config.toml` | OpenHands LLM + sandbox + MCP config |
| `ADV7ia/deploy/openhands/compose.yaml` | OpenHands container (runtime binding addr) |

**Command cheat-sheet**
```bash
docker compose up -d / down / ps / logs -f litellm     # gateway lifecycle (in gateway/)
docker port mesh-litellm                               # confirm binds
bash gateway/mint-key.sh <alias> <budget> <dur>        # new virtual key
curl 127.0.0.1:4000/v1/{models,chat/completions} ...   # use the API
claude mcp list                                        # MCP health
docker exec hermes hermes -z "..."                     # run_hermes path
sudo tailscale serve --bg 4000 ; tailscale serve status # remote
```

---

*Keep this guide in sync with `RUNBOOK.md` when ops steps change. Commit prefix:
`projects/agent_mesh:`.*
