# ADR 0008: YARA Through Loki-RS

## Decision

Use Loki-RS and YARA rules for scheduled local scans.

## Reason

YARA is best used as targeted file scanning rather than continuous blocking here.

## Consequence

Hits require manual triage during the tuning window.
