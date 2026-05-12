---
project: OpenBox
type: source-note
category: Automation
source_path: usr/local/sbin/openbox-tor-check.sh
tags:
  - openbox
  - automation
  - source-note
---

# Automation - Openbox Tor Check

## Role
verifica circuito Tor via check.torproject.org

## Source
- Path: `usr/local/sbin/openbox-tor-check.sh`
- Open: [source](../../../usr/local/sbin/openbox-tor-check.sh)
- Lines: 23

## Related Notes
- [[README]]
- [[TOR_STREAMING_CAVEAT]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `shopt -s inherit_errexit`
- `RESPONSE="$(curl --max-time 30 \`
- `--socks5-hostname 127.0.0.1:9050 \`
- `-s https://check.torproject.org/api/ip 2>/dev/null || echo '{"IsTor":false,"error":"curl_failed"}')"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
