# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context

bbWebScan is a Python project nested under the `ObsidianAgent` meta-vault.
Project contract lives in `README.md` + `CHANGELOG.md` (no separate design doc).
The parent meta-vault's `CLAUDE.md` (`../../CLAUDE.md`) governs vault generation;
this file scopes only bbWebScan engineering work.

Domain: scope-aware bug bounty web recon orchestrator. Offensive-security tooling —
any reference work / external citations must go through the `cyberref` skill
(vault-bounded). Do not paste raw upstream tool docs into source.

## Stack

- Python 3.12+, Pydantic v2, PyYAML, Rich (menu), optional `publicsuffix2`
- Single source of truth for version: `pyproject.toml`. `__version__` reads via
  `importlib.metadata`. `tests/test_changelog.py` fails if a version bump skips
  `CHANGELOG.md`.

## Commands

Run from `Projects/bbWebScan/`.

```bash
source .venv/bin/activate
pip install -e '.[dev,cov]'              # ',psl' for full publicsuffix2

ruff check .
mypy                                     # --strict per pyproject
pytest -q --cov                          # 85% line coverage gate (fail_under)
pytest -q tests/test_changelog.py        # single test
pytest -q -k "scope_gate"                # filter by keyword

bbwebscan --version
bbwebscan doctor                         # toolchain readiness; exit 2 if missing
bbwebscan history --limit 10
bbwebscan                                # interactive Rich menu (no args)
bbwebscan scan example.com               # smart-default scan
```

## Layout

- `bbwebscan/` — package (CLI in `cli.py` / `menu*.py`, models, scope gate)
- `bbwebscan/stages/` — one module per external tool: `httpx_stage`,
  `katana_stage`, `discovery_stage` (ffuf+kiterunner), `params_stage`,
  `nuclei_stage`, `amass_stage`, `kiterunner_stage`. Each stage is a pure
  function over a `RunContext`; outputs land in `runs/<UTC>/<stage>/`.
- `bbwebscan.py` (repo root) — thin shim; canonical entry point is the
  `bbwebscan` console script declared in `pyproject.toml`.
- `profiles/` — saved scan profile YAMLs. `auth.headers` / `auth.cookies`
  support `${ENV_VAR}` interpolation only; raw secrets must never be written
  to disk here.
- `runs/<UTC>/` — per-run artefacts (`summary.md`, `findings.jsonl`,
  `run_config.json`). `run_config.json` redacts auth values
  (keys preserved, values → `<redacted>`).
- `tests/fixtures/` — JSONL fixtures for stage parsers.
- `vault/` — project-local Obsidian vault (`Generated/` under it is machine-managed).

## Exit codes (`bbwebscan scan`)

- `0` ok
- `2` preflight error (missing tool / wordlist)
- `3` findings present at or above `--severity` threshold (CI gate)

`--check-dns` is non-fatal: unresolvable hosts become a note in `summary.md`.

## Conventions

- Aggressive scans + amass active/intel modes require `--ack-authorized`.
  Never bypass this gate, even in tests — gate the test behind the flag too.
- Saved profiles must not persist raw-request file paths; those are one-off
  run inputs (regression guarded; see v0.5.2 in `CHANGELOG.md`).
- Menu handlers catch `FileNotFoundError`, `FileExistsError`, `ValueError`,
  `OSError` and return to the menu — do not let them propagate as tracebacks.
- Dry-run argv echo masks `Authorization:` and `Cookie:` header values.
  Stages that pass a secret via a non-header argv slot (e.g. `jwt_tool -t <token>`)
  must set `CommandPlan.redact_indices=[i, ...]` listing the secret-bearing
  positions; the runner masks them before the dry-run echo and before any log
  write. See `bbwebscan/stages/jwt_tool_stage.py` for the canonical pattern.
- Determinism: same inputs + same run dir → byte-identical `summary.md` /
  `findings.jsonl`. Sort before writing; do not embed wall-clock outside of
  the run-dir name.
- Commit prefix for changes here: `projects/bbwebscan:` (per meta-vault commit
  convention). Bump `pyproject.toml` version AND `CHANGELOG.md` in the same
  commit — the changelog test enforces it.

## Gotchas

- The `bbwebscan` script and the in-repo `bbwebscan.py` shim both exist;
  prefer the console-script entry point when adding integration tests.
- `doctor` exit 2 is the same code as scan preflight failure; CI logic that
  branches on exit code must also inspect which subcommand ran.
- `cyberref` is the only sanctioned channel for external offensive-tool
  references in commits/PRs. Inline upstream prose without a vault citation
  is a review blocker.
