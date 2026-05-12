---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/09-validate.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - 09 Validate

## Role
validacao final

## Source
- Path: `install.d/09-validate.sh`
- Open: [source](../../../install.d/09-validate.sh)
- Lines: 14

## Related Notes
- [[README]]
- [[RUNBOOK]]

## Highlights
- `shopt -s inherit_errexit`
- `. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"`
- `run bash "${OPENBOX_ROOT}/tests/validate-stack.sh"`
- `echo "[09-validate] Para report completo: sudo lynis audit system"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
