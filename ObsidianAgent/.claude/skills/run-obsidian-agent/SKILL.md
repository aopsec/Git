---
name: run-obsidian-agent
description: Build, run, and drive ObsidianAgent. Use when asked to start ObsidianAgent, run its tests, check vault state, sync vault notes, run the CyberPDF extractor, screenshot the vault, or interact with the running agent.
---

ObsidianAgent is a CLI meta-vault orchestrator that reads `.aops-vault.toml` contracts and renders Markdown notes into `Vault/Generated/` for Obsidian. It is driven via `python3` calls to an external CLI at `$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py`. The interaction harness is `.claude/skills/run-obsidian-agent/smoke.sh`.

All paths below are relative to `ObsidianAgent/`.

## Prerequisites

The external CLI comes from the `aops-agent` plugin tree — it is **not** vendored here:

```bash
export AOPS_OBSIDIAN_AGENT_CLI="$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py"
test -f "$AOPS_OBSIDIAN_AGENT_CLI" && echo "CLI present" || echo "MISSING — check aops-agent clone"
```

Python packages needed for the tests and CyberPDF extractor:

```bash
pip install pytest pypdf2 tomli  # or whatever is declared in pyproject.toml
```

Locale must be set for deterministic glob ordering:

```bash
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
```

## Setup

No install step — the CLI is external. Run the bootstrap check above, then proceed.

## Run (agent path)

Use the smoke driver. Run from `ObsidianAgent/`:

```bash
export LC_ALL=C.UTF-8 LANG=C.UTF-8
bash .claude/skills/run-obsidian-agent/smoke.sh all
```

| command | what it does |
|---|---|
| `all` (default) | check vault state + pytest + CyberPDF dry-run |
| `check` | report stale/orphan vault files (read-only) |
| `sync` | run `--check` then `--sync` to regenerate `Vault/Generated/` |
| `test` | run pytest against `tests/test_cyber_pdf_ref.py` |
| `cyber-dry` | dry-run CyberPDF extractor — lists 11 PDF records with page/char counts |
| `stack` | run `tests/validate-collab-stack.sh` (20/25 checks pass — see Gotchas) |

Direct CLI calls (when you need one operation without the driver):

```bash
# Check vault drift (read-only):
python3 "$AOPS_OBSIDIAN_AGENT_CLI" --check --repo .

# Regenerate Vault/Generated/:
python3 "$AOPS_OBSIDIAN_AGENT_CLI" --sync --repo .

# CyberPDF extractor dry-run:
python3 tools/extract_cyber_pdf_reference.py \
  --pdf-list tools/cyber_pdf_ref/b00ks_sources.txt --repo . --dry-run

# Full rebuild (live write):
python3 tools/extract_cyber_pdf_reference.py \
  --pdf-list tools/cyber_pdf_ref/b00ks_sources.txt --repo . --copy-pdfs --replace
```

## Run (human path)

```bash
# Same as agent — this is a CLI, no separate UI.
export LC_ALL=C.UTF-8 LANG=C.UTF-8
bash .claude/skills/run-obsidian-agent/smoke.sh all
```

## Test

```bash
export LC_ALL=C.UTF-8 LANG=C.UTF-8
pytest -q tests/test_cyber_pdf_ref.py
```

Expected: `10 passed` with no warnings.

OpenBox sub-project tests:

```bash
bash Projects/OpenBox0.1v/tests/ci-syntax-check.sh
bash Projects/OpenBox0.1v/tests/validate-obsidian-vault.sh
bash Projects/OpenBox0.1v/tests/validate-stack.sh
```

---

## Gotchas

- **CLI file is not executable (+x)** — the plugin filesystem is read-only; `./$CLI` fails. Always call `python3 "$AOPS_OBSIDIAN_AGENT_CLI"`, never `"$AOPS_OBSIDIAN_AGENT_CLI"` directly.

- **`--sync` refuses with orphan files** — if `Vault/Generated/Session Logs/` contains files not in `.aops-vault.toml`'s session catalog (e.g. `2026-04-26-rk3229-retarget-report.md`), `--sync` hard-aborts. Fix: remove or register the orphan, then retry sync.

- **`validate-collab-stack.sh` expects `~/ObsidianAgent/`** — 5 of 25 checks look for the vault at `$HOME/ObsidianAgent/` (without the `OPia/Git/` prefix). These fail on this machine. The 20 that pass cover CPR skills, PreCompact hook, redactor, Codex bridge, and systemd units. The 5 path-mismatch failures are environmental, not code bugs.

- **pycache write fails in `ci-syntax-check.sh`** — `py_compile obsidian_agent/__init__.py` fails with "Read-only file system" when trying to write `.pyc` to the plugin tree. Not a syntax error — the module is valid Python.

- **`LC_ALL=C.UTF-8` is required** — without it, glob ordering for `source_patterns` is locale-dependent and `--check` may report spurious drift.

## Troubleshooting

- **`MISSING: external CLI not reachable`**: The `aops-agent` plugin was not cloned or `$AOPS_OBSIDIAN_AGENT_CLI` points to the wrong path. Verify `ls $HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py`.

- **`Refusing to sync while managed orphan files exist`**: Remove orphans from `Vault/Generated/Session Logs/` or add them to the session catalog in `.aops-vault.toml`. Then re-run `--sync`.

- **`10 passed` becomes fewer on pytest**: Check `tests/test_cyber_pdf_ref.py` — it imports from `tools/extract_cyber_pdf_reference.py`. If a PDF is moved or renamed the corresponding test fixture will fail.
