---
project: OpenBox
type: source-note
category: Systemd
source_path: systemd/openbox-dnsleak-check.timer
tags:
  - openbox
  - systemd
  - source-note
---

# Systemd - Openbox Dnsleak Check Timer

## Role
Source note for `/home/aops/ObsidianAgent/Projects/OpenBox0.1v/systemd/openbox-dnsleak-check.timer`.

## Source
- Path: `systemd/openbox-dnsleak-check.timer`
- Open: [source](../../../systemd/openbox-dnsleak-check.timer)
- Lines: 10

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `Description=OpenBox DNS leak check daily`
- `OnCalendar=daily`
- `Persistent=true`
- `RandomizedDelaySec=1h`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
