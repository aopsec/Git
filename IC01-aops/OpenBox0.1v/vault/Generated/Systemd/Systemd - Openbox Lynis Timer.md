---
project: OpenBox
type: source-note
category: Systemd
source_path: systemd/openbox-lynis.timer
tags:
  - openbox
  - systemd
  - source-note
---

# Systemd - Openbox Lynis Timer

## Role
Source note for `/home/aops/ObsidianAgent/Projects/OpenBox0.1v/systemd/openbox-lynis.timer`.

## Source
- Path: `systemd/openbox-lynis.timer`
- Open: [source](../../../systemd/openbox-lynis.timer)
- Lines: 10

## Related Notes
- [[README]]

## Highlights
- `Description=OpenBox Lynis weekly audit (Mon 03:00)`
- `OnCalendar=Mon *-*-* 03:00:00`
- `Persistent=true`
- `RandomizedDelaySec=30min`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
