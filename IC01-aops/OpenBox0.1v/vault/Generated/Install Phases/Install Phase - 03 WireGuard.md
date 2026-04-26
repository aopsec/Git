---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/03-wireguard.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - 03 WireGuard

## Role
WireGuard com fwmark routing

## Source
- Path: `install.d/03-wireguard.sh`
- Open: [source](../../../install.d/03-wireguard.sh)
- Lines: 46

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[HARDENING_PLAN_v2]]
- [[RUNBOOK]]

## Highlights
- `shopt -s inherit_errexit`
- `install_wg_ordering_override() {`
- `local target="/etc/systemd/system/wg-quick@wg0.service.d/openbox-ordering.conf"`
- `printf 'DRY: write %s\n' "${target}"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
