---
project: OpenBox
type: source-note
category: Automation
source_path: usr/local/sbin/openbox-killswitch.sh
tags:
  - openbox
  - automation
  - source-note
---

# Automation - Openbox Killswitch

## Role
kill switch helper (re-aplica nftables atomic ruleset)

## Source
- Path: `usr/local/sbin/openbox-killswitch.sh`
- Open: [source](../../../usr/local/sbin/openbox-killswitch.sh)
- Lines: 70

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `has_table() {`
- `local family="$1"`
- `local name="$2"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
