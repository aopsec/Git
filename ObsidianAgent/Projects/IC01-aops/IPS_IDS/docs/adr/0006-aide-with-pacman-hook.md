# ADR 0006: AIDE With Pacman Hook

## Decision

Install an AIDE pacman post-transaction hook.

## Reason

Arch package upgrades otherwise create large integrity false-positive sets.

## Consequence

The baseline updates after package changes; suspicious non-pacman drift remains visible.
