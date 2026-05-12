---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/05-tor.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - 05 Tor

## Role
Tor hardened

## Source
- Path: `install.d/05-tor.sh`
- Open: [source](../../../install.d/05-tor.sh)
- Lines: 33

## Related Notes
- [[README]]
- [[TOR_STREAMING_CAVEAT]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `shopt -s inherit_errexit`
- `run env DEBIAN_FRONTEND=noninteractive apt install -y tor torsocks nyx python3-stem`
- `[[ -f /etc/tor/torrc.original ]] || run cp /etc/tor/torrc /etc/tor/torrc.original`
- `run install -m 0644 -o debian-tor -g debian-tor "${OPENBOX_ROOT}/etc/tor/torrc.example" /etc/tor/torrc`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
