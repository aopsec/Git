---
project: OpenBox
type: source-note
category: Validation
source_path: tests/validate-stack.sh
tags:
  - openbox
  - validation
  - source-note
---

# Validation - Validate Stack

## Role
OpenBox v0.1 final validation

## Source
- Path: `tests/validate-stack.sh`
- Open: [source](../../../tests/validate-stack.sh)
- Lines: 95

## Related Notes
- [[README]]
- [[RUNBOOK]]

## Highlights
- `shopt -s inherit_errexit`
- `echo "===== OpenBox v0.1 — Stack Validation ====="`
- `[[ "$(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null)" == "bbr" ]] \`
- `&& ok "TCP BBR ativo" || nok "TCP BBR NAO ativo"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
