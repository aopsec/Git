# CLAUDE.md

This repository now centers on the active ADV7Sec 1.0 Python runtime.

## Current Scope

- Entry point: `ADV7Sec_1.0v.py`
- Core runtime: `adv7sec_1_0/`
- Packaged resources: `adv7sec_1_0/resource_files/`
- Active tests: `tests/test_adv7sec_cli.py`, `tests/test_adv7sec_install.py`
- Active gate: `tests/ci-syntax-check.sh`

## Working Rules

- Treat `adv7sec_1_0/` as the single source of truth.
- Use the unified CLI for audit, doctor, backend, install, monitor, analyze, respond, and smoke.
- Do not reintroduce parallel installers or duplicate source trees.
- Keep runtime resources packaged under `adv7sec_1_0/resource_files/`.

## Validation

```bash
bash tests/ci-syntax-check.sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 ADV7Sec_1.0v.py audit --format json
```
