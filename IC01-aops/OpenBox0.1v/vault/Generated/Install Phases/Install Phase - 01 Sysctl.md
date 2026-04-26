---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/01-sysctl.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - 01 Sysctl

## Role
kernel tuning

## Source
- Path: `install.d/01-sysctl.sh`
- Open: [source](../../../install.d/01-sysctl.sh)
- Lines: 31

## Related Notes
- [[README]]
- [[HARDENING_PLAN_v2]]
- [[CASE_STUDY]]

## Highlights
- `shopt -s inherit_errexit`
- `. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"`
- `run install -m 0644 "${OPENBOX_ROOT}/etc/sysctl.d/99-openbox.conf" /etc/sysctl.d/99-openbox.conf`
- `run sysctl --system`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
