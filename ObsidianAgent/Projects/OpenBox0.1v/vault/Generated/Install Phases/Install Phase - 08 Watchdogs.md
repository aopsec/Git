---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/08-watchdogs.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - 08 Watchdogs

## Role
WG, Tor, DNS leak, ntfy

## Source
- Path: `install.d/08-watchdogs.sh`
- Open: [source](../../../install.d/08-watchdogs.sh)
- Lines: 31

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `run install -m 0755 "${OPENBOX_ROOT}/usr/local/sbin/openbox-ntfy-send.sh" /usr/local/sbin/openbox-ntfy-send.sh`
- `run systemctl daemon-reload`
- `printf 'DRY: conditionally enable openbox-wg-watchdog.timer after wg-quick@wg0.service is enabled\n'`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
