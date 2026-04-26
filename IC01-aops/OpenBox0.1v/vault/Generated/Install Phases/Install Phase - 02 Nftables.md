---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/02-nftables.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - 02 Nftables

## Role
firewall + kill switch

## Source
- Path: `install.d/02-nftables.sh`
- Open: [source](../../../install.d/02-nftables.sh)
- Lines: 47

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[HARDENING_PLAN_v2]]
- [[RUNBOOK]]

## Highlights
- `shopt -s inherit_errexit`
- `append_openbox_include() {`
- `local target="/etc/nftables.conf"`
- `return 0`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
