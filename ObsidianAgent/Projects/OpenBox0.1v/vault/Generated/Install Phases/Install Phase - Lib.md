---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/_lib.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - Lib

## Role
shared helpers for OpenBox phase scripts.

## Source
- Path: `install.d/_lib.sh`
- Open: [source](../../../install.d/_lib.sh)
- Lines: 32

## Related Notes
- [[README]]

## Highlights
- `run_sh() {`
- `detect_eth_iface() {`
- `local iface`
- `iface="$(ip route show default 2>/dev/null | awk '/^default/ {print $5; exit}')"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
