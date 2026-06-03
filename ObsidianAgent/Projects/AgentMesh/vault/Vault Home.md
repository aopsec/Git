# AgentMesh Vault Home

Manual entry note for the AgentMesh project-local vault.

AgentMesh unifies the local AI stack into one mesh: planners (Claude, Copilot) dispatch to
executors (Hermes, OpenCode, OpenHands) over MCP, on a single LiteLLM gateway (GPU-local),
with remote multi-user access via Tailscale + per-user virtual keys.

- **Docs** — `docs/ARCHITECTURE.md`, `docs/HARDENING.md`, `docs/RUNBOOK.md`
- **Gateway** — `gateway/` (LiteLLM + Postgres + mesh-ollama)
- **MCP** — `mcp/` (shared fs/git/vault + executor tools)

> `Generated/` is machine-managed by `obsidian_agent_cli.py` — never edit by hand.
