# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

WslDroid provisions a **WSL2 Ubuntu** environment with **Waydroid** Android (Android 13,
LineageOS) running in an LXC container, exposed through the **WSLg** GUI, with the Google
**Play Store** (GAPPS) and **ADB** wired up. It is a phased bash installer: `install.sh`
orchestrates numbered phase scripts under `install.d/`, each idempotent and individually
runnable via `--phase`.

## Commit prefix

`projects/wsl_droid:` — all commits for this project must use this prefix. Do not invent
other prefixes; this follows the monorepo `projects/<slug>:` scheme (slug in lowercase
snake_case).

## Before committing

Run the syntax gate from the project root:

```bash
bash tests/ci-syntax-check.sh
```

It must pass (bash -n + shellcheck clean) before any commit.

## Bash conventions

- Shebang: `#!/usr/bin/env bash`
- `set -euo pipefail` and `shopt -s inherit_errexit` at the top of every script
- shellcheck-clean required (no suppressed warnings without a documented reason)
- All variables double-quoted; functions declare locals with `local`

## Phase scripts

Phase scripts live in `install.d/`, numbered `00`–`06`, and `source` `_lib.sh` for shared
helpers (`log`, `run`, `detect_wsl2`, `detect_binder`). Phases:

| Phase | Role |
|---|---|
| `00-base` | Base packages and WSL2 guard |
| `01-gui` | WSLg / Wayland setup |
| `02-kernel` | WSL2 kernel with `binder_linux` |
| `03-waydroid` | Waydroid GAPPS install + init |
| `04-adb` | ADB setup + environment profile |
| `05-gapps` | Google device certification |
| `06-validate` | Integration smoke tests |

## Do not

- Hand-edit files in `Vault/Generated/` — those are machine-managed; regenerate via the
  agent CLI instead.
- Paste external security references into source without going through the `cyberref` skill
  (vault-bounded, authorized-testing context only) — review blocker.

## Known gaps

- GPU acceleration on WSL2 + Waydroid is partially broken (MESA issue) — render may fall
  back to software rendering. See microsoft/WSL#14033.
