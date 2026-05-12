---
project: OpenBox
type: source-note
category: Automation
source_path: usr/local/sbin/openbox-tune.sh
tags:
  - openbox
  - automation
  - source-note
---

# Automation - Openbox Tune

## Role
CAKE qdisc + IRQ affinity. Chamado pela openbox-tuning.service

## Source
- Path: `usr/local/sbin/openbox-tune.sh`
- Open: [source](../../../usr/local/sbin/openbox-tune.sh)
- Lines: 40

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `_default_iface() {`
- `local i`
- `i="$(ip route show default 2>/dev/null | awk '/^default/ {print $5; exit}')"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
