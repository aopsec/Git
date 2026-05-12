---
project: OpenBox
type: source-note
category: Systemd
source_path: systemd/openbox-tuning.service
tags:
  - openbox
  - systemd
  - source-note
---

# Systemd - Openbox Tuning Service

## Role
Source note for `/home/aops/ObsidianAgent/Projects/OpenBox0.1v/systemd/openbox-tuning.service`.

## Source
- Path: `systemd/openbox-tuning.service`
- Open: [source](../../../systemd/openbox-tuning.service)
- Lines: 14

## Related Notes
- [[README]]

## Highlights
- `Description=OpenBox network tuning (CAKE qdisc + IRQ affinity)`
- `After=network-online.target`
- `Wants=network-online.target`
- `Type=oneshot`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
