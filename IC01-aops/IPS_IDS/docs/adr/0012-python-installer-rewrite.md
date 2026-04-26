# ADR 0012: Python Installer Rewrite

## Decision

Unify the installer and control plane behind the Python entrypoint `ADV7Sec_1.0v.py`
and the `adv7sec_1_0/` runtime package. Runtime wrappers and configuration remain
packaged resources, but the old Bash and parity-port installer trees are no longer
part of the active repository layout.

## Reason

The bash installer grew past the ergonomics of its shell: 12 phase scripts share
mutable env via exports, pipelines drop errors silently outside `inherit_errexit`
subshells, and testability is limited to `bash -n` plus a smoke run. A recent
external review produced seven findings of which only one held up against the
source — the other six misread the control flow. A structured Python port makes
that class of mistake expensive: function signatures, typed Context, mocked
`subprocess.run`, and phase-level unit tests pin behavior the reviewer tried to
"fix."

## Consequence

- Python 3.12+ becomes a host precondition. Arch ships it; footprint is zero.
- The parity guarantee moved into typed unit tests, strict lint/type gates, and
  staged `install --apply` validation in the active runtime.
- The old Bash installer and parity-port tree have already been removed from the
  active project layout.
- This ADR does not change Phase 1 scope (ADR 0002), sensor choices (ADR 0003,
  0004, 0005, 0009), or response policy (ADR 0010). It changes form, not behavior.

## Regression Fences

The unified runtime must preserve these invariants:

- `/etc/pacman.d/hooks/90-aide-update.hook` never promotes `aide.db.gz`. The
  pacman exec preserves the new database as `aide.db.candidate-<stamp>.gz` and
  writes a report to `/var/log/aide/`. Evidence for Phase 2 review must survive
  a `pacman -Syu`.
- `/usr/local/bin/loki-rs` is the canonical binary path regardless of upstream
  release asset name (`loki-rs`, `loki`, or `loki-util`). Timer and service
  assume this path.
- auditd smoke trigger runs `sudo /usr/bin/id` and searches `ausearch -k root-cmd`
  matching `etc/audit/rules.d/50-persistence.rules`. The key is `root-cmd`, not
  `root_escalation` or similar.
- Kunai is installed from a pinned upstream release asset with SHA256
  verification. Live branch builds are not accepted.
- Loki-RS is built from a pinned 40-character commit (`IPSIDS_LOKI_RS_REF`)
  enforced by `require_pinned_commit`. Live branch builds are not accepted.
- `aur_exists` short-circuits in dry-run unless `IPSIDS_LIVE_VALIDATE=1` is
  explicitly set. Dry-run produces no network traffic by default.
- Suricata phase ships workstation overrides via `etc/suricata/ipsids-overrides.yaml`
  (JA3/JA4 fingerprinting, exception-policy=ignore, AF_PACKET block-size=128k)
  loaded through `--include`. The vendor `/etc/suricata/suricata.yaml` is not
  edited in place.

## Status

Implemented by the active ADV7Sec 1.0 runtime.
