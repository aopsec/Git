---
project: OpenBox
type: source-note
category: Automation
source_path: usr/local/sbin/openbox-container-running.sh
tags:
  - openbox
  - automation
  - source-note
---

# Automation - Openbox Container Running

## Role
[FIX-AUDIT-MONIT] Exit 0 only when a named Docker container exists and is running.

## Source
- Path: `usr/local/sbin/openbox-container-running.sh`
- Open: [source](../../../usr/local/sbin/openbox-container-running.sh)
- Lines: 14

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `exit 1`
- `STATE="$(docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
