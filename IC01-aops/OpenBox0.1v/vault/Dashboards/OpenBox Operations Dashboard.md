---
project: OpenBox
type: dashboard
tags:
  - openbox
  - dashboard
  - operations
---

# OpenBox Operations Dashboard

## Operational Docs
- [[RUNBOOK]]
- [[README]]

## Runtime Components
- [[Systemd Service Index]]
- [[Automation Index]]
- [[Validation Index]]

## Standard Loops
- Install or reconfigure a phase: start in [[Install Phase Index]].
- Diagnose an unhealthy service: pivot through [[RUNBOOK]] and [[Systemd Service Index]].
- Re-check repository-generated notes: run `bash tests/validate-obsidian-vault.sh`.

## Operator Questions
- What needs to be enabled manually after bootstrap?
- Which health checks are authoritative versus heuristic?
- Which alerts restart services automatically and which only notify?
