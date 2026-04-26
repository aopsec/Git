---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/00-base.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - 00 Base

## Role
OpenBox base hardening

## Source
- Path: `install.d/00-base.sh`
- Open: [source](../../../install.d/00-base.sh)
- Lines: 61

## Related Notes
- [[README]]
- [[HARDENING_PLAN_v2]]
- [[RUNBOOK]]

## Highlights
- `shopt -s inherit_errexit`
- `install_unattended_upgrades_config() {`
- `local target="/etc/apt/apt.conf.d/50unattended-upgrades.local"`
- `printf 'DRY: write %s\n' "${target}"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
