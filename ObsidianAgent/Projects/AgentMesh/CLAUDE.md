# AgentMesh — Engineering Guide

Unifies the box's local AI stack into one mesh: **planners** (Claude, Copilot) drive
**executors** (Hermes, OpenCode, OpenHands) over **MCP**, on a **single LiteLLM gateway**.
Product framing in `README.md` (pt-br); architecture in `docs/ARCHITECTURE.md`; security in
`docs/HARDENING.md`; ops in `docs/RUNBOOK.md`. Additive to the meta-vault contract.

## Components
- **Gateway** (`gateway/`): LiteLLM `127.0.0.1:4000` + Postgres (virtual keys/budgets/audit)
  + **mesh-ollama** (GPU via CDI; `hermes3`, `qwen2.5-coder`). Separate from HermesAgent's
  own air-gapped ollama (deliberate — don't dissolve that isolation).
- **MCP** (`mcp/`): shared `mcp-fs-mesh.sh` (repo), `mcp-git-mesh.sh` (repo), `mcp-vault-mesh.sh`
  (Obsidian vault); executor `exec_mesh.py` (FastMCP: `run_hermes`/`run_opencode`/`run_openhands`).
  Wrappers reuse the installed servers in `~/.local/mcp-servers/` (no network).
- **Wiring**: Claude `OPia/Git/.mcp.json` (verified ✓), Copilot `OPia/Git/.vscode/mcp.json`
  (`servers` key), OpenCode `~/.config/opencode/opencode.json` `mcp` block.
- **Remote**: Tailscale overlay + per-user LiteLLM virtual keys.

## Key facts / decisions
- **Local-only** by default (Phase 2 cloud deferred). LM Studio kept as a fallback (not
  retired). HermesAgent stays on its own air-gapped ollama.
- Gateway models: `hermes3`, `qwen2.5-coder`, alias `qwen3-coder-local` → qwen2.5-coder.
- Agents authenticate to the gateway with **scoped virtual keys**, never the master key
  (master key lives only in `gateway/.env`, gitignored).

## Gotchas
- **mesh-ollama ≠ HermesAgent ollama.** Two Ollama instances share the GPU (load on demand);
  both at once can pressure 12 GB VRAM — fine for single-user, watch for concurrent load.
- **OpenHands MCP needs a stdio→HTTP bridge** (SuperGateway): its MCP servers launch INSIDE
  its container, so host stdio wrappers don't apply. Pairs with the remote/MCP-over-HTTP work.
- **Cline MCP** = guided VS Code UI step (extension state in `~/.cline`), not a repo file.
- **`tailscale serve` needs HTTPS enabled in the tailnet admin** (one-time). Until then use
  the tailnet-IP bind (WireGuard-encrypted) — see `docs/RUNBOOK.md`.
- `.mcp.json` / `.vscode/mcp.json` use **absolute** host paths (single-box); not portable as-is.
- LiteLLM virtual keys/budgets persist in Postgres (`mesh-pg` volume) — back it up before teardown.

## Verify
- Gateway: `curl 127.0.0.1:4000/v1/models -H "Authorization: Bearer <key>"`; chat routes to GPU.
- MCP: `claude mcp list` → fs/git/vault/exec ✓ Connected.
- Executor: `docker exec hermes hermes -z "ping"` (the `run_hermes` path).

## Commit prefix
`projects/agent_mesh:`
