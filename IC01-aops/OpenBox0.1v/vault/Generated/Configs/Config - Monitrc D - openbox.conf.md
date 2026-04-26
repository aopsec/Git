---
project: OpenBox
type: source-note
category: Configs
source_path: etc/monit/monitrc.d/openbox.conf
tags:
  - openbox
  - config
  - source-note
---

# Config - Monitrc D - openbox.conf

## Role
auto-restart de servicos criticos

## Source
- Path: `etc/monit/monitrc.d/openbox.conf`
- Open: [source](../../../etc/monit/monitrc.d/openbox.conf)
- Lines: 53

## Related Notes
- [[README]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `set httpd port 2812 and use address 127.0.0.1`
- `allow 127.0.0.1`
- `allow admin:REPLACE_WITH_PASSWORD`
- `set alert root@localhost not on { instance, action }`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
