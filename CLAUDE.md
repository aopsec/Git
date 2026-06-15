# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

The `aopsec/Git` monorepo — Alcides Olivo Pollazzon Soterio's (AOPS) public portfolio:
offensive-security tooling, university coursework, and AI-assisted-development infrastructure.
Primary language of prose, commits, and docs is **pt-BR**; match it when editing existing
files (code identifiers stay English).

This is not one application. It is a tree of mostly-independent projects, each carrying its
own contract. The root level only ties them together (GitHub Pages, the shared MCP mesh, and
the commit/determinism conventions below). **Do the real engineering inside the project
subtree, governed by that project's own `CLAUDE.md`.**

## Where the authoritative guidance lives

Always defer to the nested `CLAUDE.md` for a project's domain — these are detailed and current,
this root file is only the map:

| Path | Scope |
|---|---|
| [ObsidianAgent/CLAUDE.md](ObsidianAgent/CLAUDE.md) | The meta-vault: vault generation, `.aops-vault.toml` schema, CyberPDF extractor, ceremonies. **Most cross-cutting conventions originate here.** |
| [ObsidianAgent/Projects/ADV7_0f_Sec_Tools/bbWebScan/CLAUDE.md](ObsidianAgent/Projects/ADV7_0f_Sec_Tools/bbWebScan/CLAUDE.md) | bbWebScan (the most active Python project): recon orchestrator engineering. |
| [ObsidianAgent/Projects/AgentMesh/CLAUDE.md](ObsidianAgent/Projects/AgentMesh/CLAUDE.md) | Local AI mesh (LiteLLM gateway + MCP wrappers + executors). |
| [ObsidianAgent/Projects/HermesAgent/CLAUDE.md](ObsidianAgent/Projects/HermesAgent/CLAUDE.md) | Air-gapped Hermes executor (Docker/Ollama). |
| [ObsidianAgent/Projects/IPS_IDS/CLAUDE.md](ObsidianAgent/Projects/IPS_IDS/CLAUDE.md) · [ObsidianAgent/Projects/IC01-aops/IPS_IDS/CLAUDE.md](ObsidianAgent/Projects/IC01-aops/IPS_IDS/CLAUDE.md) | IPS/IDS installer (Arch) and ADV7Sec runtime. |
| [ObsidianAgent/Projects/OpenBox0.1v/ADV7Box/CLAUDE.md](ObsidianAgent/Projects/OpenBox0.1v/ADV7Box/CLAUDE.md) · [ObsidianAgent/Projects/IC01-aops/AVAL01-IC/CLAUDE.md](ObsidianAgent/Projects/IC01-aops/AVAL01-IC/CLAUDE.md) | Derived AV01 CEUB deliverables — **read-only references, not sources.** |
| [ObsidianAgent/Projects/adv7YT/CLAUDE.md](ObsidianAgent/Projects/adv7YT/CLAUDE.md) | C#/.NET 8 WPF YouTube downloader (the only Windows-native build). |

`ObsidianAgent/` also keeps an [AGENTS.md](ObsidianAgent/AGENTS.md) (Codex sibling) and
`.github/copilot-instructions.md`. Those three (CLAUDE / AGENTS / copilot) are kept in
**parity** — changing a convention in one means updating the others, or the Claude↔Codex↔Copilot
guidance diverges.

> Drift warning: the **root** [.github/copilot-instructions.md](.github/copilot-instructions.md)
> is partly stale — it documents a `blk7rch/` project that is not in this tree and pre-move
> paths (e.g. `ObsidianAgent/Projects/bbWebScan/`, now under `.../ADV7_0f_Sec_Tools/bbWebScan/`,
> and `IC01-aops/` at root, now under `Computer_Science/1SEM/` and `ObsidianAgent/Projects/`).
> Trust the nested `CLAUDE.md` files and the live tree over it.

## Top-level layout

```
.
├── ObsidianAgent/        Meta-vault + all active Projects/ (see table above). The center of gravity.
├── Computer_Science/     Academic work: 1SEM/{BootCamp1,FreeCodeCamp,Logica_Programacao_I,
│                         Mat4Comp,IC01-aops,...} and HTB/ writeups. Python exercises + course PDFs.
├── KALInit/              Kali/Arch provisioning shell scripts (init.sh, nwscpt*.sh).
├── wordlists/            SecLists-style wordlists + custom (see wordlists/README.md, INDEX.md).
├── index.md / README.md  GitHub Pages portfolio (pt-BR).
├── _config.yml           Jekyll config; excludes every source/vault dir from Pages rendering.
├── .mcp.json             Claude MCP wiring → AgentMesh fs/git/vault/exec servers.
└── .github/workflows/    pages.yml (Pages deploy), adv7yt-publish.yml.
```

## Cross-cutting conventions (apply repo-wide)

- **Commit prefixes** — semantic, scoped to subsystem: `vault:`, `tests:`, and
  `projects/<slug>:` where slug is lowercase snake_case (`projects/bbwebscan:`,
  `projects/openbox:`, `projects/agent_mesh:`, `projects/ips_ids:`). Do not invent prefixes
  outside this scheme.
- **Determinism** — anything generated (vault notes, indexes) must be byte-identical for the
  same repo state. Export `LC_ALL=C.UTF-8 LANG=C.UTF-8` before any vault sync/compare so glob
  ordering matches across machines.
- **`Vault/Generated/` is machine-managed** — never hand-edit; regenerate via the agent CLI.
- **Offensive-security code is vault-bounded** — external reference prose must be cited through
  the `cyberref` skill, not pasted into source (review blocker). Authorized-testing context only.
- **Code style** — Python: `ruff` (line-length 120) + `mypy --strict` where configured; Bash:
  shellcheck-clean, `set -euo pipefail` (documented deviations exist, e.g. OpenBox
  `validate-stack.sh` uses `set -uo pipefail` intentionally to accumulate PASS/FAIL).

## Most-used commands

The high-frequency workflows live in nested guides; the essentials:

```bash
# ObsidianAgent meta-vault (run from ObsidianAgent/) — external CLI required, see its CLAUDE.md
export AOPS_OBSIDIAN_AGENT_CLI="${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}"
export LC_ALL=C.UTF-8 LANG=C.UTF-8
python3 "$AOPS_OBSIDIAN_AGENT_CLI" --check --repo .   # then --sync, then --check again (must be clean)
bash .claude/skills/run-obsidian-agent/smoke.sh all   # check + pytest + cyber-dry-run

# bbWebScan (run from Projects/ADV7_0f_Sec_Tools/bbWebScan/) — single quality gate
bash scripts/verify.sh                                 # ruff + mypy --strict + pytest --cov (≥98%)
pytest tests/test_<module>.py::TestClass::test_name -v # single test

# OpenBox fixture (run from Projects/OpenBox0.1v/)
bash tests/ci-syntax-check.sh                          # bash -n + shellcheck + nft + py_compile
```

## Environment gotcha (Windows host, Linux-native tooling)

This checkout runs on Windows, but the repo's automation is Linux-native and assumes an
`/home/aops/OPia/Git/...` checkout:

- **`.mcp.json` uses absolute `/home/aops/...` paths** to AgentMesh wrapper scripts — they do
  not resolve on Windows as-is and are single-box, not portable.
- The ObsidianAgent CLI is **external and not vendored** (`$HOME/plugins/aops-agent/...`); all
  `--check`/`--sync` commands fail without it. Run the smoke-test guard in
  [ObsidianAgent/CLAUDE.md](ObsidianAgent/CLAUDE.md) before relying on vault commands.
- Most build/test scripts are Bash; use the Bash tool (WSL/git-bash) for them. Only
  `Projects/adv7YT/` builds natively on Windows (.NET 8 WPF).
