---
project: OpenBox
type: source-note
category: Automation
source_path: usr/local/sbin/openbox-wg-watchdog.sh
tags:
  - openbox
  - automation
  - source-note
---

# Automation - Openbox WG Watchdog

## Role
verifica handshake WireGuard, restart se > THRESHOLD

## Source
- Path: `usr/local/sbin/openbox-wg-watchdog.sh`
- Open: [source](../../../usr/local/sbin/openbox-wg-watchdog.sh)
- Lines: 45

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]

## Highlights
- `shopt -s inherit_errexit`
- `logger -t openbox-wg-watchdog "wg command absent — skipping watchdog"`
- `exit 0`
- `logger -t openbox-wg-watchdog "${UNIT} disabled — skipping watchdog"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
