---
project: OpenBox
type: source-note
category: Automation
source_path: usr/local/sbin/openbox-ntfy-send.sh
tags:
  - openbox
  - automation
  - source-note
---

# Automation - Openbox Ntfy Send

## Role
helper para enviar notificacao via ntfy local

## Source
- Path: `usr/local/sbin/openbox-ntfy-send.sh`
- Open: [source](../../../usr/local/sbin/openbox-ntfy-send.sh)
- Lines: 30

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `http://127.*|http://localhost*|"http://[::1]"*)`
- `*)`
- `logger -t openbox-ntfy "Rejected non-local NTFY_URL: ${NTFY_URL}"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
