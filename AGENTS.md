# AGENTS.md

This file helps AI coding agents ramp up on the `aopsec/Git` monorepo quickly.

## What this repo is

A portfolio monorepo — offensive-security tooling, university coursework, and AI-assisted-development infrastructure. **Not one application.** Each subtree is an independent project with its own contract. Root level only ties them together (GitHub Pages, shared MCP mesh, commit conventions).

**Primary language of prose, commits, and docs is pt-BR.** Match it when editing existing files (code identifiers stay English).

## Where authoritative guidance lives

**Always defer to the nested `CLAUDE.md`** for a project's domain. The root `CLAUDE.md` is the map; the nested files are the territory.

| Path | Scope |
|---|---|
| `ObsidianAgent/CLAUDE.md` | Meta-vault orchestration — vault generation, `.aops-vault.toml`, CyberPDF extractor. **Most cross-cutting conventions originate here.** |
| `ObsidianAgent/Projects/ADV7_0f_Sec_Tools/bbWebScan/CLAUDE.md` | Python recon orchestrator (most active project). |
| `ObsidianAgent/Projects/AgentMesh/CLAUDE.md` | Local AI mesh (LiteLLM gateway + MCP wrappers). |
| `ObsidianAgent/Projects/HermesAgent/CLAUDE.md` | Air-gapped Hermes executor (Docker/Ollama). |
| `ObsidianAgent/Projects/adv7YT/CLAUDE.md` | C#/.NET 8 WPF YouTube downloader (only Windows-native build). |
| `ObsidianAgent/Projects/IPS_IDS/CLAUDE.md` | IPS/IDS installer (Arch) and ADV7Sec runtime. |
| `ObsidianAgent/Projects/OpenBox0.1v/ADV7Box/CLAUDE.md` | AV01 CEUB deliverable — read-only reference. |

`ObsidianAgent/AGENTS.md` is the Codex-side sibling. Keep it in parity with `CLAUDE.md`.

## Top-level layout

```
.
├── ObsidianAgent/        Meta-vault + all active Projects/ — the center of gravity
├── Computer_Science/     Academic work: 1SEM/{BootCamp1,FreeCodeCamp,Logica_Programacao_I,IC01-aops,...} + HTB writeups
├── KALInit/              Kali/Arch provisioning shell scripts
├── wordlists/            SecLists-style wordlists + custom
├── index.md / README.md  GitHub Pages portfolio (pt-BR)
├── _config.yml           Jekyll config — excludes source/vault dirs from Pages
├── .mcp.json             Claude MCP wiring → AgentMesh fs/git/vault/exec servers (uses /home/aops/... paths)
└── .github/workflows/    pages.yml (Pages deploy), adv7yt-publish.yml
```

> **Drift warning:** The root `.github/copilot-instructions.md` is partly stale — it documents a `blk7rch/` project no longer in the tree and pre-move paths. Trust the nested `CLAUDE.md` files and the live tree over it.

## Cross-cutting conventions

- **Commit prefixes** — semantic, scoped: `vault:`, `tests:`, `projects/<slug>:` (slug = snake_case, e.g. `projects/bbwebscan:`, `projects/openbox:`, `projects/agent_mesh:`, `projects/ips_ids:`). Do not invent prefixes outside this scheme.
- **Determinism** — generated vault notes must be byte-identical for the same repo state. Always `export LC_ALL=C.UTF-8 LANG=C.UTF-8` before vault sync/compare.
- **`Vault/Generated/` is machine-managed** — never hand-edit; regenerate via the agent CLI.
- **Offensive-security code is vault-bounded** — external references must go through the `cyberref` skill, not pasted into source (review blocker). Authorized-testing context only.
- **Code style** — Python: `ruff` (line-length 120) + `mypy --strict`; Bash: shellcheck-clean, `set -euo pipefail`.

## Key commands

### ObsidianAgent meta-vault (from `ObsidianAgent/`)

The external CLI is **not vendored** in this repo (`$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py`). If missing, all vault commands fail.

```bash
export AOPS_OBSIDIAN_AGENT_CLI="${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}"
export LC_ALL=C.UTF-8 LANG=C.UTF-8
python3 "$AOPS_OBSIDIAN_AGENT_CLI" --check --repo .   # then --sync, then --check again (must be clean)
bash .claude/skills/run-obsidian-agent/smoke.sh all   # check + pytest + cyber-dry-run
```

### bbWebScan (from `Projects/ADV7_0f_Sec_Tools/bbWebScan/`)

```bash
bash scripts/verify.sh                                 # ruff + mypy --strict + pytest --cov (≥98%)
pytest tests/test_<module>.py::TestClass::test_name -v # single test
```

### OpenBox fixture (from `Projects/OpenBox0.1v/`)

```bash
bash tests/ci-syntax-check.sh                          # bash -n + shellcheck + nft + py_compile
```

### adv7YT (Windows-native)

```bash
dotnet build && dotnet test                            # requires .NET 8 SDK
```

## Environment gotcha

This checkout runs on **Windows**, but most automation is **Linux-native** and assumes `/home/aops/OPia/Git/...`:

- **`.mcp.json` uses absolute `/home/aops/...` paths** — will not resolve on Windows.
- Most build/test scripts are Bash — use WSL or git-bash.
- Only `Projects/adv7YT/` builds natively on Windows (.NET 8 WPF).
- The ObsidianAgent CLI is external and not vendored — run the smoke-test guard before relying on vault commands.

## Testing quirks

- **OpenBox `validate-stack.sh`** uses `set -uo pipefail` (no `-e`) — accumulates PASS/FAIL, does not abort on first failure. Don't confuse with root-level `tests/validate-collab-stack.sh` which uses `set -euo pipefail`.
- **OpenBox is Debian/Raspbian** (apt) — installer scripts won't run on Arch without adaptation.
- **bbWebScan** enforces coverage ≥98% via `pytest --cov` and CHANGELOG sync via `test_changelog.py` (version bump without changelog update = fail).
- **adv7YT CI** creates stub binaries before test build — real `yt-dlp.exe`/`ffmpeg.exe` are downloaded and patched into `ToolHashes.cs` during publish.

## Nested AGENTS.md / CLAUDE.md files

- `ObsidianAgent/AGENTS.md` — Codex-side guidance (keep in parity with CLAUDE.md).
- `ObsidianAgent/Projects/askmaps-eval/AGENTS.md` — project-specific.
- Each active project has its own `CLAUDE.md` — read it before editing that project.
