# ADR 0011: Local Journald First

## Decision

Use journald and local log files as the first alert sink.

## Reason

The project is a single-host baseline, not a centralized SOC deployment.

## Consequence

External sinks must be added deliberately after Phase 2 tuning.
