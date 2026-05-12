---
session: rk3229-retarget
date: 2026-04-26
project: OpenBox0.1v (cascade: ADV7Box)
operator: aops
status: code+docs complete; hardware execution pending
---

# OpenBox v0.2.0 — RK3229 retarget session report

## 1. Mandate

Operator request (paraphrased):
> "Substitute the Raspberry Pi 4 reference platform with a generic Shenzhen
> Rockchip RK3229 board (R29_5G_LP3); complete 100% of the 7-phase migration
> plan; certify the project first; produce a consolidated doc report; then
> hand off to the operator for hardware-side execution. Also research FCC
> filings and known backdoors for the board."

Source plan: `/home/aops/.claude/plans/radiant-launching-valley.md` (approved
2026-04-25).

## 2. Decisions locked at plan time

| Decision | Choice | Why it matters for what was done |
|---|---|---|
| Migration scope | **Full retarget** (drop RPi 4) | All edits are removals + replacements, not multi-target branches. Code is simpler but RPi 4 path is gone. |
| Distro | **Armbian community `rk322x-box`** | Keeps apt + systemd + in-tree WireGuard, so most install.d/ phases stay structurally intact. |
| Board | **One physical R29_5G_LP3 unit on hand** | Phase 0 fingerprinting can be empirical; no speculative branching required. |

## 3. Phases executed (workstation-side)

### Phase 0 — fingerprinting tooling (preparation; execution is operator's)
- Wrote `Projects/OpenBox0.1v/tools/fingerprint-rk3229.sh` (12 probes,
  formatted output, gate criteria documented inline).
- Operator runs it on the booted Armbian unit; output goes to
  `Projects/OpenBox0.1v/docs/hw/r29_5g_lp3.txt`.

### Phase 1 — distro flash (operator-side, not executed)
- Plan documents the maskrom-mode flash flow for the R29_5G_LP3 (V1.1 / V1.2
  / V2.3 / V3.0 PCB revisions) using `rkdeveloptool` against an Armbian
  community `rk322x-box` minimal image (Bookworm, kernel ≥ 6.x).
- Plan also forbids first-boot of the stock Android image on any network
  (one of BadBox 2.0's three infection vectors triggers there).

### Phase 2 — code edits (workstation-side, complete)
13 file changes in `Projects/OpenBox0.1v/`:

| File | Change |
|---|---|
| `install.sh` | Version → 0.2.0; Raspbian message → Armbian/Debian armhf; `armhf` arch guard added; phase list `06-stremio` → `06-media`. |
| `install.d/_lib.sh` | Added 4 runtime probes: `detect_eth_iface`, `ram_kb`, `has_cpufreq`, `arch_is_armhf`. Comment cross-ref updated. |
| `install.d/00-base.sh` | Removed Raspbian apt origin from unattended-upgrades (Armbian publishes under `origin=Debian`). |
| `install.d/06-stremio.sh` → `install.d/06-media.sh` | Renamed; rewrote for Jellyfin (`jellyfin/jellyfin:latest` publishes `linux/arm/v7`; Stremio does not). Port 8080 → 8096. |
| `install.d/07-monitoring.sh` | Updated 2 historical comments naming the old phase script. |
| `etc/sysctl.d/99-openbox.conf` | TCP buffer ceilings 16 MB → 4 MB (rmem/wmem/tcp_rmem/tcp_wmem); comment updated to "1GB LPDDR3 RK3229". |
| `usr/local/sbin/openbox-tune.sh` | IFACE autodetected via default-route; BANDWIDTH default 85mbit → 95mbit; cpufreq governor write guarded behind existence check. |
| `etc/monit/monitrc.d/openbox.conf` | Memory alert 85 % → 92 %; Stremio container check renamed to Jellyfin. |
| `etc/caddy/Caddyfile` | `/stremio/*` → `/jellyfin/*`; backend `:8080` → `:8096`; banner updated. |
| `etc/nftables/openbox-base.nft` | Stremio DSCP rule ports `{8080, 11470, 12470}` → Jellyfin port `8096`. |
| `tests/validate-stack.sh` | CAKE check uses autodetected IFACE; cpufreq governor check guarded; Lynis target relaxed 75 → 70 (first run). |
| `VERSION` | `0.1.0` → `0.2.0` |
| `CHANGELOG.md` | Added v0.2.0 entry with Changed / Added / Replaced / Tuned-for-1GB sections. |
| `README.md` | Hardware target rewritten; comparison table updated; ASCII architecture diagram updated; Quick Start adds Phase 0 fingerprint step; Status line reflects v0.2.0. |

### Phase 3 — acceptance criteria revision (placeholders only)
The audit numbers (WireGuard sustained throughput ≥ 90 Mbps, RAM headroom
≥ 200 MB, boot < 180 s, Lynis ≥ 70 / ≥ 75 after tuning, idle CPU < 70 °C) are
**placeholders** in `radiant-launching-valley.md`. They become real numbers only
after the operator runs `openssl speed -evp chacha20` (Phase 0 probe 0.12) and
a 60-second iperf3 test through the WireGuard tunnel on the booted unit.

The .ms (groff) audit report at
`Projects/OpenBox0.1v/deliverables/AV01_OpenBox_Audit_Report.ms` was **not**
edited this session — its hardware-target prose still references the RPi 4
baseline. Rationale: the .ms is a frozen academic deliverable for AV01-A
(submitted 2026-04-18); the v0.2.0 retarget is a *successor* version, not a
restatement of the same submission. The HTML/PDF in `Projects/ADV7Box/` is the
forward-looking deliverable and *was* updated.

### Phase 4 — documentation cascade (complete except for placeholder numerics)
- CHANGELOG, VERSION, README updated (above).
- `docs/security/RK3229_THREAT_RESEARCH.md` written (8.5 KB; 9 sections + 12
  cited sources; covers maskrom hardware backdoor, BadBox 2.0, Vo1d,
  partition layout, post-flash verification commands, public hardware
  documentation sources, defensive operational checklist).
- ADV7Box.html: 27 substitutions across §0 metadata, §2.1 separation,
  §3 architecture (SVG title + label + ASCII), §4 Pillar A (egress diagram +
  components table + phase list), §6 BOM (RPi-row → RK3229-row, R$ 805 → R$
  195), §6.3 software stack (Stremio → Jellyfin), §7 threat model (added
  maskrom note + BadBox/Vo1d supply-chain bullet), §8.1 install order
  (added wipe-via-maskrom step), §12 ADR cross-ref (`06-stremio.sh` →
  `06-media.sh`), §13 trade-offs (RPi vs RK3229 row rewritten), §14
  limitations (shakedown target now RK3229 physical), §15.1 timeline (added
  2026-04-25 retarget marker), §15.3 roadmap (cluster RPi → cluster RK3229),
  §19.5 / §19.9 references (added Rockchip datasheet, MattWestb teardown,
  CNX teardown, FBI IC3 PSA, Vo1d coverage, Maskrom wiki).
- ADV7Box.pdf regenerated via `chromium --headless=new --virtual-time-budget=10000`;
  900 KB output (was 875 KB), 2026-04-26 00:33.
- OpenBox vault sync ran clean after removing one managed-orphan note
  (`Install Phase - 06 Stremio.md`); 6 generated notes refreshed.
- Meta-vault sync ran clean; no regen needed (meta-vault renders Project
  Overview as link stubs, not body copies).

### Phase 5 — board-side validation (operator-side, not executed)
Per the plan's verification block, requires the operator to run on the booted
unit: `tests/ci-syntax-check.sh`, `sudo OPENBOX_DRY_RUN=1 ./install.sh`,
`sudo ./install.sh`, `sudo bash tests/validate-stack.sh`, the smoke commands
(`wg show`, `dig @127.0.0.1`, `curl --socks5-hostname 127.0.0.1:9050`,
`nft list ruleset`, `systemctl is-active`), iperf3 over the tunnel, and
`systemd-analyze`.

### Phase 6 — risk register
Already documented in `radiant-launching-valley.md` §"Risks and mitigations"
(8 ranked risks + mitigations). Reproduced here in the threat doc for the
hardware-specific subset (BadBox 2.0, Vo1d, maskrom).

### Phase 7 — out-of-scope explicit
- No custom Armbian image build.
- No cross-compilation of Stremio for armhf (Jellyfin substitution makes this
  moot).
- No multi-board variant support (one PCB, one image).
- No mainline kernel patching.
- No RPi 4 code paths preserved.

## 4. Threat research summary

Three threat tiers documented in
`Projects/OpenBox0.1v/docs/security/RK3229_THREAT_RESEARCH.md`:

1. **Maskrom mode (silicon, cannot be disabled)** — physical attacker shorts
   PCB pad → re-flashes arbitrary firmware. Mitigation is physical only
   (tamper-evident enclosure). Treat physical-access-equals-game-over.

2. **BadBox 2.0 (supply chain, FBI IC3 PSA250605)** — ~10M devices in Google
   lawsuit (Jul 2025). Built on Triada. Three vectors: pre-installed firmware,
   first-boot OTA, sideload from unofficial app stores. **Specifically targets
   the device class the operator is sourcing** (generic Chinese Android TV
   boxes including MXQ Pro 4K family). Public IoCs: `catmore88[.]com`,
   `ycxrl[.]com` and one-letter variants, `duoduodev[.]com`, `flyermobi[.]com`,
   `motiyu[.]net`, `qazwsxedc[.]xyz` (109 IoC domains total per HUMAN
   Security; 5 M+ subdomains sinkholed 2025-04-10).

3. **Vo1d (Doctor Web, 2024-09)** — ~1.3 M devices in 197 countries.
   Substitutes `/system/bin/debuggerd` (renaming original to `debuggerd_real`),
   drops `/system/xbin/vo1d` and `/system/xbin/wd`. **Brazil leads the
   infection list** — directly relevant to the operator's geography. Wiped
   entirely by full eMMC flash + Armbian install (no BootROM persistence).

**FCC angle**: R29_5G_LP3 is a generic OEM PCB used inside many branded SKUs;
no FCC ID applies to the bare PCB. Public technical documentation sources
(higher-signal than FCC for this PCB family) catalogued in §6 of the threat
doc — Rockchip datasheet V1.2, MattWestb's V2.3 teardown repo, CNX Software
2016 teardown (identifies NANYA `NT5CB256M16CP-D1` DRAM, Pulse `H1102NL`
Ethernet magnetics, **Espressif ESP8089** Wi-Fi, unpopulated 3-pin serial
console header).

**FBI/FOIA**: vault.fbi.gov returns no Rockchip-specific declassified material
as of 2026-04-26. The IC3 PSA250605 is the FBI's substantive public communication
on this device class; no IoCs in the PSA itself (that's standard FBI PSA
practice — IoCs come from security vendors).

## 5. Files created or modified (consolidated)

### Created (4)
- `Projects/OpenBox0.1v/install.d/06-media.sh` (replaces `06-stremio.sh`)
- `Projects/OpenBox0.1v/tools/fingerprint-rk3229.sh`
- `Projects/OpenBox0.1v/docs/security/RK3229_THREAT_RESEARCH.md`
- `Projects/ADV7Box/CLAUDE.md` (created earlier in this session by `/init`)
- `~/ObsidianAgent/SessionLogs/OpenBox/2026-04-26-rk3229-retarget-report.md` (this file)

### Modified (13 in OpenBox + 1 in ADV7Box)
- `Projects/OpenBox0.1v/{install.sh, VERSION, CHANGELOG.md, README.md}`
- `Projects/OpenBox0.1v/install.d/{_lib.sh, 00-base.sh, 07-monitoring.sh}`
- `Projects/OpenBox0.1v/etc/sysctl.d/99-openbox.conf`
- `Projects/OpenBox0.1v/etc/monit/monitrc.d/openbox.conf`
- `Projects/OpenBox0.1v/etc/caddy/Caddyfile`
- `Projects/OpenBox0.1v/etc/nftables/openbox-base.nft`
- `Projects/OpenBox0.1v/usr/local/sbin/openbox-tune.sh`
- `Projects/OpenBox0.1v/tests/validate-stack.sh`
- `Projects/ADV7Box/ADV7Box.html` (27 substitutions) → `ADV7Box.pdf` regenerated

### Deleted (1)
- `Projects/OpenBox0.1v/vault/Generated/Install Phases/Install Phase - 06 Stremio.md`
  (managed orphan; deletion documented in vault stale-detection section above)

### Vault syncs (2)
- OpenBox vault: 6 notes regenerated (Automation/Configs/Install Phases/Validation indices).
- Meta-vault: 0 notes regenerated (Project Overview is link-stub, not body-embed).

## 6. Certification state

**Workstation-side (this session)**:
- `bash tests/ci-syntax-check.sh` baseline: **74 pass / 0 fail**
- `bash tests/ci-syntax-check.sh` after all edits: **76 pass / 0 fail**
  (+2 = shellcheck on `06-media.sh` and `fingerprint-rk3229.sh`)
- All `.sh` scripts pass `bash -n` and `shellcheck`
- All systemd unit headers validate
- All Python files compile
- All TOML parses
- Obsidian vault: in-sync, no stale entries

**Board-side (operator's responsibility)**:
- Phase 0 fingerprint capture: **pending**
- Phase 1 boot baseline: **pending**
- Phase 2 actual install (`sudo ./install.sh`): **pending**
- Phase 5 stack validation (`validate-stack.sh`): **pending**
- iperf3 throughput measurement: **pending** (number feeds Phase 3 audit)
- systemd-analyze boot timing: **pending** (number feeds Phase 3 audit)

## 7. Operator handoff — exact next steps

1. **Acquire the unit.** Do not power-on on any network until step 4.

2. **Source materials**:
   - Armbian community minimal `rk322x-box` Bookworm image:
     `https://www.armbian.com/rk322x-box/`
   - `rkdeveloptool` (Arch: `pacman -S rkdeveloptool`; or build from source).
   - GitHub teardown for the closest PCB revision to confirm maskrom pad
     location: `https://github.com/MattWestb/R29-MXQ-LP3-V2.3-00908`.

3. **Maskrom flash** the Armbian image to eMMC (USB-OTG cable to a development
   host; short the maskrom pad while plugging in USB).

4. **First boot on a wired Ethernet to a trusted network**. SSH in, then run:
   ```bash
   sudo bash tools/fingerprint-rk3229.sh > docs/hw/r29_5g_lp3.txt 2>&1
   ```

5. **Verify the 4 gate criteria** (read `docs/hw/r29_5g_lp3.txt`):
   - Section 0.1: `compatible` contains `rockchip,rk3229` or `rockchip,rk3228`
   - Section 0.2: `armv7l` and `armhf`
   - Section 0.7: `modinfo wireguard` returns module info
   - Section 0.10: at least one `/dev/watchdog*` exists

6. **If any gate fails**: stop. Re-flash with a different Armbian rk322x
   variant. Do not proceed.

7. **If gates pass**:
   ```bash
   bash tests/ci-syntax-check.sh        # static gates
   sudo OPENBOX_DRY_RUN=1 ./install.sh  # dry-run preview
   sudo ./install.sh                    # real install
   sudo bash tests/validate-stack.sh    # 10 functional checks
   ```

8. **Throughput baseline** (record in `docs/hw/r29_5g_lp3.txt`):
   ```bash
   iperf3 -c <wg-peer-internal-ip> -t 60        # upload via tunnel
   iperf3 -c <wg-peer-internal-ip> -t 60 -R     # download via tunnel
   ```

9. **Boot timing** (record same):
   ```bash
   systemd-analyze
   systemd-analyze blame | head -20
   ```

10. **Update Phase 3 acceptance numbers** in
    `Projects/OpenBox0.1v/deliverables/AV01_OpenBox_Audit_Report.ms` (or
    successor doc) with the real measured values from steps 8 + 9.

## 8. Known gaps / honest disclosures

- **No board-side verification was performed in this session.** All claims
  about RK3229 behavior (WireGuard throughput, RAM headroom, boot time,
  thermal) are predictions from public sources, not measurements.
- **Armbian rk322x-box DTS may not match this PCB's exact peripheral set.**
  Phase 0.1 + 0.6 will detect this; a mismatch means picking a different
  Armbian variant or accepting reduced peripheral support.
- **Stremio → Jellyfin is a feature change, not a like-for-like swap.**
  Jellyfin requires a media library; Stremio's add-on/streaming model is
  different. Operator should confirm Jellyfin meets the actual use case
  before committing.
- **The .ms audit report was not updated** — see Phase 3 rationale.
- **Meta-vault Project Overview did not regen** — confirms it's a link-stub
  rather than a content embed. Operator may want to manually open
  `~/ObsidianAgent/Vault/Generated/Project Overviews/Project Overview - OpenBox.md`
  to confirm display.

## 9. References (used this session, beyond what's already in the threat doc)

- Plan file (this session): `/home/aops/.claude/plans/radiant-launching-valley.md`
- Project CLAUDE.md (meta): `/home/aops/ObsidianAgent/CLAUDE.md`
- Project CLAUDE.md (ADV7Box, created this session): `/home/aops/ObsidianAgent/Projects/ADV7Box/CLAUDE.md`
- OpenBox install harness: `Projects/OpenBox0.1v/install.sh`, `install.d/`
