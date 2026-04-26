---
project: ADV7ia
type: operations-note
tags:
  - adv7ia
  - session-ledger
---

# Session Ledger

## Current Session

- Session: `session-bootstrap-openhands`
- Role: `session_manager`
- Status: `compact_pending`
- Token state: `31400 / 32768`

## Renewal Rules

- Roll the session at `95%` token usage.
- Link every new session to its parent and checkpoint.
- Store compaction notes under `vault/Operations/Compactions/`.
