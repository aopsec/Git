---
project: OpenBox
type: source-note
category: Automation
source_path: usr/local/sbin/openbox-dnsleak-check.sh
tags:
  - openbox
  - automation
  - source-note
---

# Automation - Openbox Dnsleak Check

## Role
DNS leak check (referencia: macvk/dnsleaktest)

## Source
- Path: `usr/local/sbin/openbox-dnsleak-check.sh`
- Open: [source](../../../usr/local/sbin/openbox-dnsleak-check.sh)
- Lines: 74

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `shopt -s inherit_errexit`
- `declare -a OBSERVED_NAMESERVERS=()`
- `notify_failure() {`
- `local message="$1"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
