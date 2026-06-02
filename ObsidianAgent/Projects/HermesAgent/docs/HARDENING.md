# HermesAgent — Hardening Rationale

Why each control exists, mapped to **primary sources**. Upstream Hermes docs are the
authority on the agent's threat model; the local `HTB/Cyber_Jr/Structure_InfoSec.md`
module and the certified **CyberPDF** vault provide the InfoSec framing. CyberPDF
references are **copyright-bounded**: operational summaries + source pointers only, no
reproduced chapters (per the `cyberref` contract).

> Repo-relative paths below are from the meta-vault root (`ObsidianAgent/`): the InfoSec
> module is `../../HTB/Cyber_Jr/Structure_InfoSec.md` and the CyberPDF vault is
> `../../Vault/References/CyberPDFs/`.

## Threat model (from Hermes `SECURITY.md`)

The agent processes untrusted input (messages, web content, files) with an LLM that can be
adversarially steered (prompt injection). Hermes states plainly:

> *"The only security boundary against an adversarial LLM is the operating system."*

In-process approval prompts, redaction, and allowlists are **heuristics, not containment**.
Hermes describes two OS-level postures: *terminal-backend isolation* (sandbox just the shell
tool) and *whole-process wrapping* (run the entire agent inside a container). **Whole-process
wrapping is the supported posture for untrusted input + production** — and is what this
deployment uses (`docker-compose.yml`, `image: hermes-agent:local`). It also documents what
the wrap does **not** contain: in-process code-execution and MCP tools are not sandboxed by
the wrap — only shell/file tools are (see Residual Risks).

---

## Control → source map

### 1. Network Security — egress isolation
**Control:** Two Docker networks — `internal` (`internal: true`, no default route) and
`egress` (internet). `ollama` is internal-only (air-gapped inference). `gateway` is
dual-homed but all outbound HTTP(S) is forced through the Squid proxy
(`HTTP_PROXY`/`HTTPS_PROXY`), which is **deny-all** except an explicit allowlist
(`squid/squid-allowlist.conf`). `dashboard` is internal-only.

**Sources:**
- Hermes `docs/security/network-egress-isolation.md` — *"primarily a defense against prompt
  injection attacks that attempt to exfiltrate data via `curl`, `wget`, or raw HTTP."* The
  `internal`/`egress` split, dual-homed gateway, and `http_access deny all` allowlist pattern
  are taken directly from this doc.
- `Structure_InfoSec.md` §Network Security — firewalls as "barriers between trusted internal
  networks and untrusted external networks, filtering traffic based on predetermined security
  rules." The Squid allowlist is exactly such a predetermined-rule barrier; the no-route
  `internal` network is the trusted segment.
- CyberPDF vault (`Vault/References/CyberPDFs/`) — exfiltration / C2 egress-prevention
  technique pointers (Technique Index). Summary: outbound allowlisting and egress filtering
  break the data-exfil and beaconing stages of post-compromise activity; see the certified
  Sources notes for the specific references. *(cyberref-bounded: pointer only.)*

### 2. Application Security — least privilege in the container
**Control:** Non-root `hermes` user (UID 10000, remappable via `HERMES_UID`/`HERMES_GID`);
s6-overlay as PID 1 (`/init`) preserved; no `docker` terminal backend, no `docker.sock` mount;
the cli-config is mounted read-only.

**Sources:**
- Hermes `Dockerfile` / `SECURITY.md` — non-root user, s6-overlay supervision, privilege-drop
  exec shim; "preserve `/init` as the first command in any entrypoint override."
- `Structure_InfoSec.md` §Application Security — *"Security by Design … security isn't
  something you think about later, but rather you build into the app from the start."* Running
  unprivileged with a minimal writable surface is security-by-design at the container layer.

### 3. Operational Security — secrets, logging, surface
**Control:** No LLM API key (local inference). Optional tool keys live only in `.env`
(gitignored), never committed. Session-log redaction uses the meta-vault's
`~/plugins/aops-agent/cpr/redact.py`. The dashboard is published to host **127.0.0.1 only**;
the API server stays **off**.

**Sources:**
- Hermes `docker-compose.yml` — dashboard binds localhost; *"do NOT pass `--insecure --host
  0.0.0.0`"*; API server off by default.
- `Structure_InfoSec.md` §Operational Security — *"access control … determining who should
  have access to what information and systems, and under what circumstances."* Localhost-only
  binding + key scoping + redaction are access-control and information-handling measures.
- Root `CLAUDE.md` convention — *"Redação de segredos em session logs: obrigatória via
  `~/plugins/aops-agent/cpr/redact.py`."*

### 4. Cloud / Container Security — supply chain & blast radius
**Control:** Image built from the pinned upstream Dockerfile (s6-overlay, SHA256-verified
supply chain upstream); **no `docker.sock`** mounted (no host escape); isolated git worktree
per session (`worktree: true`); `Vault/Generated/` mounted read-only to preserve the
meta-vault determinism contract.

**Sources:**
- Hermes `Dockerfile` / `SECURITY.md` — verified supply chain, whole-process wrap as the
  boundary; the `docker` backend / socket mount is explicitly the *less safe* option.
- `Structure_InfoSec.md` §Cloud Security — the *shared responsibility model*: "the cloud
  provider secures the building (the infrastructure), while you secure your own unit (your
  data and applications)." Here we own the container config: least privilege, no socket, RO
  data tree.

---

## Residual risks (documented, not hidden)

1. **Full vault RW.** The agent can mutate notes outside `Generated/`. Mitigated by the
   read-only `Vault/Generated/` bind + agent instruction; still the largest blast radius of
   the chosen options. Removing the RO bind line in `docker-compose.yml` widens it.
2. **Squid is in-container (heuristic-grade).** The gateway is dual-homed (it must reach the
   proxy on `egress`), so it technically has a route; the real hard boundary is `internal:
   true` for `ollama` (air-gapped inference). Squid is not a substitute for a host firewall.
3. **Code-exec / MCP not contained by the wrap** (per `SECURITY.md`). Only shell/file tools
   are sandboxed by whole-process wrapping. Keep MCP/code-exec tools disabled or trusted.
4. **Dashboard auth gate is OFF (`HERMES_DASHBOARD_INSECURE=1`).** No OAuth
   `DashboardAuthProvider` is configured, so Hermes would otherwise fail closed on the
   dashboard's non-loopback (`0.0.0.0`) bind. The compensating control is the
   **host-loopback-only publish** (`127.0.0.1:9119`, verified NOT reachable on the LAN IP).
   Anyone with access to the host loopback — or to the `internal`/`egress` Docker networks —
   can use the dashboard without auth: fine for a single-user workstation, NOT a shared host.
   Add an OAuth provider or an authenticating reverse proxy before exposing it.

---

## cyberref certification

- **Vault:** `Vault/References/CyberPDFs/` (certified `objective_complete=100%`).
- **Local module:** `HTB/Cyber_Jr/Structure_InfoSec.md` (Network / Application / Operational /
  Cloud Security sections).
- **Upstream primary sources:** Hermes `SECURITY.md`, `docs/security/network-egress-isolation.md`,
  `docker-compose.yml`, `cli-config.yaml.example`, `Dockerfile`.
- **Copyright posture:** summaries + source pointers only; no reproduced chapters.

**`objective_complete` gate:** mark 100% only after the LOCAL verification gates in `README.md`
/ `Makefile` pass on the RTX 4070 Ti box — GPU smoke, model GPU-offload, LLM E2E reply, egress
block/allow proofs, dashboard-not-on-LAN, and a clean meta-vault `--check`/`--sync`/`--check`
with `Vault/Generated/` untouched.
