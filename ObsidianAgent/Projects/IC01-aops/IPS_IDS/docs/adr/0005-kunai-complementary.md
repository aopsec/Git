# ADR 0005: Kunai Is Complementary

## Decision

Attempt Kunai install, but do not make Phase 1 fail if packaging is unavailable.

## Reason

Kunai package names and build layout may drift.

## Consequence

Falco and auditd remain the required host sensors.
