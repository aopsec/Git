# ADV7ia

ADV7ia is a vault-enabled local AI stack project imported into `ObsidianAgent`.
It consolidates the validated Arch Linux + LM Studio + OpenHands/Aider/Cline/OpenCode
workflow into a reviewable project directory with reproducible notes, curated host
scripts, and stable audit evidence.

## What This Project Contains

- Imported validation notes from `~/openhands-workspace/aider-test`
- Imported helper scripts from `~/bin` for stack status, MCP wrappers, and local RAG
- Stable audit evidence from `~/.local/ai-stack-audits`
- Repo-local Obsidian vault wrappers plus validation scripts for `--check` and `--sync`
- A repo-local control mesh for recursive task state, token rollover, and security gates

## Source Provenance

- Source repo content: `~/openhands-workspace/aider-test`
- Host automation wrappers: `~/bin/{ai-stack-status,audit-local-ai-stack,index-aider-test-rag,query-aider-test-rag,mcp-*-aider-test}`
- Imported guide: `~/Downloads/guia_local_ai_stack_arch_lmstudio_corrigido.md`
- Stable evidence logs: `~/.local/ai-stack-audits/*.log`

The imported project intentionally excludes ephemeral or machine-specific state such as
`.git/`, `.aider.chat.history.md`, `.aider.input.history`, `.aider.tags.cache.v4/`,
and `~/.local/ai-stack-snapshots/`.

## Layout

```text
ADV7ia/
├── README.md
├── .aops-vault.toml
├── .aider.conf.yml
├── adv7ia_control/
├── deploy/
├── docs/
├── tools/
├── tests/
├── evidence/
├── state/
└── vault/
```

- `docs/` stores the imported validation notes and setup guide.
- `adv7ia_control/` stores the repo-local controller package for checkpoints, compaction, and security gates.
- `deploy/` stores OpenHands and Caddy templates for localhost-only binding and authenticated LAN access on `adv7ia-control.home.arpa:8443`.
  It also stores the `vmtst` GNOME Boxes guest tunnel assets used for live LAN-proxy
  certification from an isolated VM.
- `tools/` keeps the original host tool names, but updates their defaults to work from
  the `ADV7ia` project where possible.
- `tests/` verifies the curated import and the Obsidian vault contract.
- `evidence/` stores representative stable audit outputs.
- `state/` stores machine-readable control-mesh policy, task, session, and checkpoint files.
- `vault/` stores manual dashboards, templates, and generated indexes.

## Quick Start

```bash
python3 main.py
bash tools/control-mesh status
bash tools/control-mesh brief
bash tools/control-mesh reconcile --plan
bash tests/validate-project-layout.sh
bash tests/validate-obsidian-vault.sh
bash tests/validate-control-mesh.sh
bash tools/ai-stack-status
bash tools/bootstrap-adv7ia-rag
bash tools/control-mesh compact --session-id session-bootstrap-openhands --force
bash tools/audit-control-mesh
bash tools/index-aider-test-rag
bash tools/query-aider-test-rag "filesystem MCP and git MCP validation"
python3 tools/sync_obsidian_vault.py --check
python3 tools/sync_obsidian_vault.py --sync
```

## Operational Notes

- `tools/mcp-git-aider-test` defaults to `~/openhands-workspace/aider-test` because the
  imported `ADV7ia` project intentionally does not carry Git history.
- `tools/mcp-filesystem-aider-test`, `tools/index-aider-test-rag`, and
  `tools/query-aider-test-rag` default to the `ADV7ia` project root, so the imported
  project stays self-contained for filesystem and RAG workflows.
- `tools/bootstrap-adv7ia-rag` seeds the default `adv7ia_repo_rag` collection only when
  it is missing, so the standard repo-query path can pass without disposable collection
  overrides.
- The vault wrappers require a valid shared Obsidian agent install. If
  `AOPS_OBSIDIAN_AGENT_HOME` is stale, the wrappers now ignore it and keep searching for a
  valid install; if none exists, they fail with a clear error and
  `tests/validate-obsidian-vault.sh` skips cleanly.
- The control mesh keeps OpenHands on `127.0.0.1:3000` and treats LAN access as a
  separate Caddy concern via `deploy/caddy/Caddyfile`, exposed as
  `https://adv7ia-control.home.arpa:8443`.
- Docker bridge sandboxes reach OpenHands through a dedicated `172.17.0.1:3000` proxy,
  which keeps `host.docker.internal:3000` working without publishing the app on
  `0.0.0.0:3000`.
- `.local` is no longer used for the LAN proxy name. The repo now standardizes on
  `adv7ia-control.home.arpa` so the hostname does not conflict with mDNS-only `.local`
  resolution.
- `deploy/bin/install-caddy-lan-proxy` installs a rootless Caddy fallback when package
  level `caddy.service` management is unavailable. It downloads the official `caddy`
  binary, generates a server CA plus a client CA, enables the user-scoped
  `adv7ia-caddy-lan-proxy.service`, and leaves the client bundle under
  `${HOME}/.local/share/adv7ia/caddy/clients/` for LAN machines that should connect.
- The current deployment target for that bridge proxy is
  `deploy/systemd-user/openhands-docker-proxy.service`. The matching
  `deploy/systemd/openhands-docker-proxy.service` unit is kept in the repo as the later
  system-scope migration target when pre-login startup or system ownership becomes
  necessary.
- The preferred Caddy deployment target remains the host `caddy.service` with
  `/etc/caddy/Caddyfile`, but this host can also run the repo-managed
  `deploy/systemd-user/adv7ia-caddy-lan-proxy.service` fallback when root access is not
  available.
- `deploy/systemd-guest/adv7ia-vmtst-reverse-tunnel.service` is the guest-side systemd
  unit that keeps a reverse SSH tunnel from the `vmtst` GNOME Boxes VM back to the host
  on `127.0.0.1:2222`.
- `deploy/bin/install-vmtst-reverse-tunnel` copies the dedicated tunnel key into the
  guest, installs that guest unit, and enables the persistent `vmtst` access path used
  for VM-originated certification.
- `state/policy/control-mesh.json` defines the recursive loop, token thresholds, and the
  approval gates for risky actions such as edits, network changes, and secret handling.
- `state/policy/openhands-reconcile.json` defines the desired live OpenHands container
  spec, the managed settings subset, and the recreate policy for live drift.
- `bash tools/control-mesh ...` can render the controller status, create checkpoints,
  plan live OpenHands drift with `reconcile --plan`, apply settings plus Compose
  recreation with `reconcile --apply`, and roll a session into
  `vault/Operations/Compactions/` when the token budget reaches `95%`.
- `reconcile --apply` prefers the OpenHands settings API when
  `ADV7IA_OPENHANDS_SETTINGS_API_URL` is set; otherwise it updates
  `${HOME}/.openhands/settings.json` directly and uses `docker compose up -d --force-recreate --wait`
  for immutable Docker drift.
- The repo-local controller dependencies live in `.venv/`; the shell wrapper prefers that
  interpreter automatically and falls back to `python3` only when the venv is absent.
- `tools/audit-local-ai-stack` now bounds the `lms status` and `lms ps` probes so a
  sleeping or stopped LM Studio instance cannot hang the full status snapshot.
- `tools/audit-control-mesh` validates the repo templates by default and can audit the
  live runtime with `--live`.
- The original source README is preserved at `docs/AIDER_TEST_SOURCE_README.md`.

## Evidence

Representative stable audit logs are stored in `evidence/`:

- `ai-stack-status.stable.2026-04-24-153505.log`
- `audit-local-ai-stack.final.2026-04-24-041947.log`
- `audit-local-ai-stack.known-good.2026-04-24-045236.log`
