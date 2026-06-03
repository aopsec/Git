# AgentMesh — Architecture

## Goal
Unify a siloed local AI stack into one mesh: **planners** (Claude, Copilot) decompose work
and **dispatch** to **executors** (Hermes, OpenCode, OpenHands) through **MCP**, all backed by
**one OpenAI-compatible LLM gateway**. Shared memory = the ObsidianAgent vault.

## Topology

```
 Planners ── Claude · Copilot · Cline(plan) ──┐
                                              ▼  (MCP)
   ┌─────────────────── MCP tool layer ───────────────────┐
   │ shared:  fs-mesh · git-mesh · vault-mesh              │
   │ executor: exec-mesh → run_hermes/run_opencode/...     │
   └───────────────┬───────────────────────┬──────────────┘
                   │ (dispatch)             │ (OpenAI API)
        Executors: Hermes·OpenCode·OpenHands│
                                            ▼
        ┌──────── LiteLLM gateway  127.0.0.1:4000 ────────┐
        │ virtual keys · budgets · routing · audit (PG)    │
        └───────────────┬──────────────────────────────────┘
                        ▼  mesh-ollama (GPU/CDI)
                   hermes3 · qwen2.5-coder
   Remote: Tailscale overlay (private, encrypted) + per-user virtual keys
   Shared memory: ObsidianAgent vault via vault-mesh MCP
```

## Layers
1. **LLM gateway** — LiteLLM (`gateway/`) is the single endpoint. `model_list` maps
   `hermes3`/`qwen2.5-coder` (+`qwen3-coder-local` alias) to **mesh-ollama** (GPU). Postgres
   holds virtual keys, budgets, and audit. Cloud providers are a deferred opt-in (Phase 2).
2. **MCP tool layer** — shared resource servers (`fs/git/vault`) reuse the installed MCP
   servers, re-pointed at the live repo + vault. The **executor MCP** (`exec_mesh.py`,
   FastMCP) turns each executor into a callable tool — this is the MCP-centric control plane.
3. **Planners** consume the MCP layer (Claude `.mcp.json` ✓ verified, Copilot
   `.vscode/mcp.json`, OpenCode `mcp` block) and route LLM calls through the gateway.
4. **Remote/multi-user** — Tailscale overlay (no public ports) + LiteLLM virtual keys give
   network-layer + app-layer auth.

## Why two Ollamas
HermesAgent keeps its **own air-gapped ollama** (its hardening contract); the mesh runs a
**separate mesh-ollama** the gateway can reach. They share the GPU (load on demand).

## Phase status
- **P0** ✅ meta-vault orphan fixed; HermesAgent indexed.
- **P1** ✅ gateway live, GPU-routed; OpenCode repointed via a virtual key. (Consolidation:
  LM Studio kept as fallback by choice; not retired.)
- **P2** ⏸ deferred — local-only chosen.
- **P3** ✅ shared + executor MCP; Claude+OpenCode wired+verified; Copilot config shipped.
  Deferred: OpenHands (needs SuperGateway stdio→HTTP), Cline (guided UI).
- **P4** 🟡 virtual keys/budgets working; tailnet exposure pending the tailnet HTTPS/Serve
  admin toggle (see RUNBOOK).
- **P5** ✅ docs + meta-vault indexing (this).

## Alternatives considered
- **Tailscale Serve vs Caddy** for TLS/remote: Serve subsumes Caddy for the tailnet case
  (TLS + MagicDNS + tailnet-only). `caddy/Caddyfile` is kept for a public/non-tailscale path.
- **Consolidate vs keep LM Studio**: kept as fallback per decision; mesh standardizes on Ollama.
