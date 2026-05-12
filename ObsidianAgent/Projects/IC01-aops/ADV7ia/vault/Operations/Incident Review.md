---
project: ADV7ia
type: operations-note
tags:
  - adv7ia
  - incident-review
---

# Incident Review

## Trigger Conditions

- OpenHands exposed on `0.0.0.0:3000`
- Caddy mutual TLS disabled or misconfigured
- Recursive task exceeded retry or depth caps
- Token rollover failed to preserve checkpoint continuity

## Response Template

1. Capture the failing checkpoint and session ids.
2. Record the runtime evidence and proxy/container state.
3. Mark the task `blocked` or `dead_letter`.
4. Document the remediation before reopening recursion.
