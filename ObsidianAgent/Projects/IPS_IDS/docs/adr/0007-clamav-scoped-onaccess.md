# ADR 0007: Scoped ClamAV OnAccess

## Decision

Limit ClamAV on-access scanning to Downloads, `/tmp`, and removable media.

## Reason

Full home-directory on-access scanning is too noisy and expensive for Phase 1.

## Consequence

Coverage favors ingress paths over exhaustive file monitoring.
