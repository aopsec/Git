<!-- [IPS-PH2] Authoritative Phase 2 tuning plan for the IPS_IDS workstation project. -->

# Phase 2 Tuning Plan

Phase 2 converts Phase 1 telemetry into a stable, low-noise workstation baseline. It does not add blocking, external alert sinks, or fleet tooling.

## Recommendation

Treat Phase 2 as an evidence-preserving tuning project, not as another package-install phase.

The correct output is a documented baseline:

- daily summaries exist for each sensor
- false positives are classified before suppression
- every suppression has a rollback path
- AIDE baseline changes are reviewed before acceptance
- Suricata and Zeek interface choices are proven with traffic
- Phase 3 response candidates are backed by measured signal

## Scope

In scope:

- auditd rule review
- Falco rule exceptions and local rule tuning
- Suricata rule disable/re-enable decisions
- Zeek interface and package telemetry validation
- Unbound dnstap health checks
- AIDE drift review and baseline promotion
- ClamAV and Loki-RS hit triage
- Lynis, arch-audit, chkrootkit, and unhide review cadence

Out of scope:

- nftables auto-blocking
- Hagezi RPZ enforcement
- CrowdSec
- fail2ban
- Wazuh
- external alert sinks
- immutable audit mode with `-e 2`

## Timeline

Run Phase 2 for 14 days unless the host is unusably noisy.

```text
Day 0      Smoke test and capture initial health snapshot
Days 1-3   Observe without suppressions unless alerts break usability
Days 4-7   Add minimal suppressions with written evidence
Days 8-13  Validate that suppression volume stays stable
Day 14     Decide: extend tuning, promote selected controls, or redesign noisy sensors
```

## Artifacts

Keep local review artifacts outside the repository, for example in an operator notebook or a private working directory.

Recommended structure:

```text
daily/
  YYYY-MM-DD.md
evidence/
  YYYY-MM-DD-tool-rule.txt
suppressions.md
aide-baseline-promotions.md
network-interface-proof.md
phase3-candidates.md
```

Do not store secrets, private keys, auth tokens, full browser histories, or sensitive file contents in these notes.

## Day 0 Baseline

Run after Phase 1 smoke tests pass:

```bash
python3 ADV7Sec_1.0v.py smoke --root /
systemctl --failed
systemctl list-timers '*aide*' '*loki*' '*lynis*' '*chkrootkit*'
sudo auditctl -s
sudo falco --list | head -50
sudo suricata --build-info | head -40
zeekctl status || true
```

Write results to your local daily note for that date.

## Daily Review

Use time windows, not tail-only review:

```bash
SINCE="yesterday"

sudo journalctl -u auditd --since "${SINCE}" --no-pager > /tmp/ipsids-auditd.log
sudo journalctl -u falco-modern-bpf.service --since "${SINCE}" --no-pager > /tmp/ipsids-falco.log
sudo journalctl -u kunai.service --since "${SINCE}" --no-pager > /tmp/ipsids-kunai.log

sudo jq -r '.event_type' /var/log/suricata/eve.json 2>/dev/null | sort | uniq -c | sort -nr
sudo jq -r 'select(.event_type=="alert") | [.alert.signature_id, .alert.signature] | @tsv' /var/log/suricata/eve.json 2>/dev/null | sort | uniq -c | sort -nr | head -30
```

Record:

- top noisy rule
- top suspicious rule
- event count by tool
- broken services
- tuning action or reason for no action

## Weekly Review

Run once per week:

```bash
sudo aide --check || true
sudo lynis audit system --quiet --no-colors || true
sudo arch-audit || true
sudo chkrootkit || true
sudo unhide quick || true
```

Record whether each result is:

- expected package churn
- known workstation behavior
- suspicious and needs investigation
- tool failure or configuration problem

## Suppression Rules

Suppress only after evidence exists.

Required fields:

- date
- tool
- rule or signature id
- raw event excerpt path
- process and command line
- user
- why it is benign
- exact config change
- validation command
- rollback command

Store decisions in your local suppression log.

## Tool-Specific Plan

### auditd

Source config:

`/etc/audit/rules.d/50-persistence.rules`

Review commands:

```bash
sudo ausearch -ts yesterday -k identity
sudo ausearch -ts yesterday -k privilege
sudo ausearch -ts yesterday -k systemd
sudo ausearch -ts yesterday -k root-cmd
```

Phase 2 actions:

- keep rules mutable; do not add `-e 2`
- reduce broad watches only after identifying repeated benign paths
- keep root command, systemd, SSH, firewall, and pacman hook visibility

Promotion gate:

- 7 consecutive days without high-volume unexplained audit churn

### Falco

Source configs:

`/etc/falco/falco.local.yaml` and `/etc/falco/rules.d/workstation.yaml`

Review commands:

```bash
sudo journalctl -u falco-modern-bpf.service --since yesterday --no-pager
sudo jq -r '.rule // empty' /var/log/falco-events.json 2>/dev/null | sort | uniq -c | sort -nr
```

Phase 2 actions:

- prefer exceptions and rule overrides over deleting rules
- keep alerts for privilege escalation, persistence, unexpected listeners, and ad hoc server tools
- document editor, terminal, browser, and package-manager exceptions separately

Validation:

```bash
sudo falco --validate /etc/falco/falco.yaml
sudo systemctl restart falco-modern-bpf.service
sudo journalctl -u falco-modern-bpf.service -n 50 --no-pager
```

Rollback:

```bash
sudo systemctl restart falco-modern-bpf.service
```

### Suricata

Source configs:

`/etc/suricata/eve-minimal.yaml` and `/etc/suricata/disable.conf`

Review commands:

```bash
sudo jq -r '.event_type' /var/log/suricata/eve.json | sort | uniq -c | sort -nr
sudo jq -r 'select(.event_type=="alert") | [.alert.signature_id, .alert.signature] | @tsv' /var/log/suricata/eve.json | sort | uniq -c | sort -nr | head -50
```

Interface proof:

- capture one browsing session without VPN
- capture one browsing session with VPN
- confirm whether `enp3s0`, `wlan0`, `wg0`, or `tun0` has the app-layer visibility needed
- document the result in your local interface-proof note

Promotion gate:

- `eve.json` has expected event types
- alert volume is reviewable daily
- disabled groups are documented
- at least one interface choice is proven with real traffic

### Zeek

Review commands:

```bash
zeekctl status
sudo find /opt/zeek/logs/current /usr/logs/current -maxdepth 1 -type f 2>/dev/null
sudo tail -n 20 /opt/zeek/logs/current/conn.log 2>/dev/null || true
```

Phase 2 actions:

- prove `conn.log`, `dns.log`, `ssl.log`, and package-specific logs exist where expected
- document whether Zeek should stay always-on or become PCAP/lab-only

Promotion gate:

- Zeek logs add useful metadata not already covered by Suricata

### Unbound Dnstap

Review commands:

```bash
systemctl is-active unbound.service
sudo test -S /run/unbound/dnstap.sock
```

Phase 2 actions:

- verify socket exists after reboot
- defer RPZ and Hagezi until Phase 3

### AIDE

Do not blindly accept baseline changes during Phase 2.

Before package updates:

```bash
sudo aide --check > /tmp/aide-before-update.txt 2>&1 || true
```

After package updates:

```bash
sudo aide --check > /tmp/aide-after-update.txt 2>&1 || true
```

Promotion rule:

- promote a new baseline only after reviewing the diff
- record the promotion in your local AIDE promotion log

Recommended hook change before production:

- archive `aide --update` output before replacing `/var/lib/aide/aide.db.gz`
- do not promote the baseline if `aide --update` fails or produces no new database
- the shipped pacman hook preserves reports and candidate databases; manual review still decides promotion

### ClamAV

Review commands:

```bash
sudo journalctl -u clamav-daemon.service --since yesterday --no-pager
sudo journalctl -u clamav-clamonacc.service --since yesterday --no-pager
sudo tail -n 100 /var/log/clamav/clamonacc.log 2>/dev/null || true
```

Phase 2 actions:

- keep `OnAccessPrevention no`
- confirm scans cover Downloads, `/tmp`, and removable media
- classify hits before delete/quarantine

Promotion gate:

- prevention remains a Phase 3 decision unless false-positive rate is zero and rollback is documented

### Loki-RS And YARA

Review commands:

```bash
systemctl list-timers loki-rs-scan.timer
sudo journalctl -u loki-rs-scan.service --since "7 days ago" --no-pager
```

Phase 2 actions:

- classify every YARA hit manually
- record rule source and file path
- never auto-delete on Phase 2 hits

### Lynis, arch-audit, chkrootkit, unhide

Review commands:

```bash
sudo lynis audit system --quick --no-colors || true
sudo arch-audit || true
sudo chkrootkit || true
sudo unhide quick || true
```

Phase 2 actions:

- convert repeated findings into hardening tasks
- do not hide findings by disabling checks unless the tool is demonstrably wrong

## Phase 3 Candidate Register

Use a local Phase 3 candidate note outside the repository.

Each candidate must include:

- signal source
- exact rule/signature
- observed count over 14 days
- false-positive count
- proposed action
- rollback command
- blast radius

Allowed Phase 3 candidates:

- selected nftables response
- Hagezi RPZ
- ClamAV prevention
- external alert sink
- CrowdSec only if inbound services justify it

## Exit Criteria

Phase 2 is complete only when:

- 14 daily notes exist, or an extension decision is documented
- no required service is failing
- alert volume is low enough for daily review
- all suppressions have evidence and rollback
- AIDE baseline promotions are documented
- Suricata and Zeek interface choices are proven
- Phase 3 candidates have false-positive counts and rollback plans

If any criterion fails, extend Phase 2 by 7 days.
