---
project: OpenBox
type: source-note
category: Automation
source_path: usr/local/sbin/openbox-lynis-notify.sh
tags:
  - openbox
  - automation
  - source-note
---

# Automation - Openbox Lynis Notify

## Role
extract lynis hardening index and send ntfy.

## Source
- Path: `usr/local/sbin/openbox-lynis-notify.sh`
- Open: [source](../../../usr/local/sbin/openbox-lynis-notify.sh)
- Lines: 8

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `idx=$(grep 'hardening_index' /var/log/lynis-report.dat 2>/dev/null | cut -d= -f2 || echo "?")`
- `/usr/local/sbin/openbox-ntfy-send.sh "openbox-audit" "Lynis weekly: ${idx}"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
