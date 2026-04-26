---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/06-media.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - 06 Media

## Role
Jellyfin media server via Docker (armhf nativo)

## Source
- Path: `install.d/06-media.sh`
- Open: [source](../../../install.d/06-media.sh)
- Lines: 64

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"`
- `write_docker_repo_file() {`
- `local target="/etc/apt/sources.list.d/docker.list"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
