# AgentMesh — Hardening & Threat Model

Cyberref-grounded. The mesh is a single-tenant→small-multi-tenant control plane for LLMs +
agent tools; the load-bearing boundary is the **OS/container + the network overlay**, not any
in-process screening (per Hermes `SECURITY.md`).

## Trust model
- **Planners/executors are not a security boundary.** An adversarial LLM (prompt injection)
  is contained by: containerization, the LiteLLM key/budget gate, the Tailscale overlay, and
  (when enabled) the egress allowlist — not by prompt rules.
- **Secrets:** the LiteLLM **master key** + Postgres password live only in `gateway/.env`
  (gitignored, `chmod 600`). Agents get **scoped virtual keys** (per-user, model-scoped,
  budgeted) — never the master key. Cloud keys (if Phase 2 is enabled) also live in `.env`.

## Controls → rationale
1. **Network (default-deny exposure).** Gateway + MCP bind **`127.0.0.1`**; remote access is
   ONLY via the **Tailscale** overlay (WireGuard-encrypted, per-device auth) — **no public
   ports**. `Structure_InfoSec.md` §Network Security: trusted-segment + predetermined rules.
2. **AuthN/Z + budgets (multi-tenant).** LiteLLM virtual keys = per-user identity; `max_budget`
   + `budget_duration` + model scoping cap blast radius and spend; Postgres audit trails calls.
3. **Egress (when cloud is enabled).** Cloud API calls go through a **Squid allowlist** limited
   to provider hosts (reuse the HermesAgent pattern) — defends against prompt-injection exfil.
   Local inference needs **no egress** (the default posture).
4. **Container least-privilege.** mesh-ollama/LiteLLM/Postgres run as containers; **no
   `docker.sock`** is mounted into any agent; the executor MCP shells fixed argv (no shell
   string) with timeouts. `Structure_InfoSec.md` §Application/Cloud Security.
5. **Vault integrity.** `vault-mesh` MCP exposes the vault RW for shared memory, but
   `Vault/Generated/` is machine-managed — drift is caught by `obsidian_agent_cli.py --check`.

## Residual risks (documented)
1. **Master key in `gateway/.env`** — protect host access; rotate if leaked (re-mint virtual keys).
2. **Two Ollamas share 12 GB VRAM** — concurrent heavy load can OOM/fallback to CPU.
3. **`.mcp.json`/`.vscode/mcp.json` absolute paths** — single-box only; not portable.
4. **OpenHands executor + Cline MCP not yet wired** (SuperGateway / extension UI) — out of the
   current trust surface until added.
5. **Tailnet membership = network trust** — anyone on the tailnet can reach the gateway (still
   needs a valid virtual key). Use tailnet ACLs to scope which devices may reach `:4000`.

## Certification gate
Mark `objective_complete=100%` only when: gateway routes to GPU ✓, `claude mcp list` all ✓,
executor dispatch returns real output ✓, virtual keys enforce scope/budget ✓, remote reachable
ONLY over the tailnet ✓, and meta-vault `--check` clean ✓.
