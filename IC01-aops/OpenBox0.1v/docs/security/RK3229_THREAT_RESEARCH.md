# RK3229 / R29_5G_LP3 — Threat research and mitigation plan

**Scope**: defensive hardening research for the OpenBox v0.2.0 retarget from
Raspberry Pi 4 to a generic Shenzhen `R29_5G_LP3` board (Rockchip RK3229 SoC).
The user owns the unit and is wiping the stock Android firmware to install
Armbian. This document captures the **pre-existing threats** that the wipe must
neutralize, and the **post-wipe verification** steps to confirm neutralization.

**Date**: 2026-04-25
**Classification**: defensive — public sources only, no exploitation guidance.

---

## 1. Hardware backdoor — Rockchip Maskrom mode

| Attribute | Value |
|---|---|
| Type | Physical / hardware-level recovery interface |
| SoC | All Rockchip SoCs including RK3229 / RK3228A |
| Disable? | **Cannot be disabled** — wired into the BootROM at silicon level |
| Trigger | Short the maskrom pad on the PCB while powering on via OTG-USB |
| Risk model | Local physical attacker can re-flash arbitrary firmware in seconds |

**Impact for OpenBox**: any attacker with physical access to the appliance can
short the maskrom test pad (documented community-wide for the rk322x family),
boot into BootROM, and flash a malicious image — bypassing every software
defense in OpenBox, including LUKS if it were present. There is no
software-side fix because BootROM runs before Linux.

**Mitigation**:
- Treat the appliance as **physical-access-equals-game-over** (already the
  default OpenBox threat model per `docs/THREAT_MODEL.md`).
- Place the unit in a tamper-evident enclosure if physical access is plausible.
- Document the maskrom pad location for the specific PCB revision (V1.1, V1.2,
  V2.3, V3.0) in `docs/hw/r29_5g_lp3.txt` so future owners know where the
  backdoor lives, rather than discovering it during an incident.

---

## 2. Supply-chain firmware backdoor — BADBOX 2.0

| Attribute | Value |
|---|---|
| Authoritative source | FBI IC3 PSA250605 (2025-06-05) |
| Discovery | HUMAN Security (Satori), Trend Micro, Bitsight, Shadowserver |
| Scale | 10M+ devices in the Google lawsuit (Jul 2025); 1M+ confirmed by Satori (Jan 2025) |
| Base malware | Triada (Android, multi-year history in low-cost devices) |
| Insertion point | Pre-purchase — backdoor flashed into firmware before retail |
| Affected device classes | Android TV streaming devices, digital projectors, vehicle infotainment, digital picture frames |
| Specific SoC named? | **No.** FBI alert is SoC-agnostic but most infected devices are Chinese-manufactured |
| C2 examples (public IoCs) | `catmore88[.]com`, `ycxrl[.]com` and its one-letter variants, `duoduodev[.]com`, `flyermobi[.]com`, `motiyu[.]net`, `qazwsxedc[.]xyz` |
| Total IoC domains (HUMAN) | 109 domains; 5M+ subdomains sinkholed on 2025-04-10 |

**Three infection vectors per the FBI PSA**:
1. **Pre-installation in firmware** before the device ships from the factory.
2. **First-boot OTA**: device contacts a malicious endpoint during initial setup
   to download and install a backdoored app.
3. **Sideload from unofficial app stores** marketed as offering "free streaming
   content".

**Why this is acute for the R29_5G_LP3**: BadBox 2.0 specifically targets
generic, no-name Chinese Android TV boxes — the exact device class the user is
sourcing. The R29_5G_LP3 is an MXQ Pro 4K reference design; MXQ-branded boxes
are repeatedly named in public BadBox/Vo1d coverage.

**Mitigation in OpenBox v0.2.0 flow**:
- **Wipe before first network connection.** Do not boot the stock Android image
  while the device is plugged into any network. The first-boot OTA vector
  triggers inside the stock OS.
- Flash Armbian `rk322x-box` to eMMC via maskrom-mode USB rkdeveloptool, NOT
  via the vendor's OTA mechanism.
- After Armbian boots, run section 5 below to verify no Android-era partitions
  survived.
- DNS sinkhole the BadBox/Vo1d IoC domains at the Pi-hole layer as defense in
  depth (even though Armbian wipe should remove the malware entirely). See
  `docs/security/blocklists/badbox-vo1d.txt` (TODO: generate from HUMAN's IoC
  feed before production).

---

## 3. Vo1d backdoor (Doctor Web, 2024-09)

| Attribute | Value |
|---|---|
| Discoverer | Doctor Web (Russian AV vendor) |
| Scale | ~1.3M Android TV boxes in 197 countries |
| Persistence mechanism | Substitutes `/system/bin/debuggerd` (rename original to `debuggerd_real`); drops `/system/xbin/vo1d` and `/system/xbin/wd` |
| Naming trick | "vo1d" mimics Android's legitimate `vold` (substituting `1` for `l`) |
| Capability | C2-driven download and execution of arbitrary third-party software |
| **Top countries hit** | **Brazil**, Morocco, Pakistan, Saudi Arabia, Argentina, Russia, Tunisia, Ecuador, Malaysia, Algeria, Indonesia |

**Direct relevance to this user**: Brazil leads Vo1d's infection list, and the
operator (per project context) is in Brasília. This is not academic — these
boxes ship from Aliexpress/Shopee infected. Treat any box-as-purchased as
compromised.

**Mitigation**: Vo1d only persists in the Android `/system` partition. A full
eMMC wipe and Armbian re-flash via maskrom mode removes it entirely. Vo1d does
not infect the BootROM (which is silicon) or U-Boot SPL (which is overwritten
by the Armbian image's `idbloader` + `u-boot.itb`). See section 5 verification.

---

## 4. Rockchip partition layout — what a wipe must overwrite

Reference: Rockchip open-source wiki — partitions table for rk322x family.

| Partition | Contents | Wiped by Armbian flash? |
|---|---|---|
| `loader1` (idbloader) | RC4-obfuscated SPL loader from BootROM | **Yes** (Armbian image overwrites sector 0x40) |
| `loader2` (u-boot.itb) | Mainline U-Boot + ATF | **Yes** |
| `trust` | TEE / OP-TEE blob | **Yes** (overwritten or absent in mainline) |
| `misc` | Recovery state | Yes |
| `boot` | Android kernel + ramdisk | Yes (replaced by Armbian rootfs) |
| `recovery` | Stock Android recovery | Yes |
| `system` / `vendor` / `oem` | Android OS partitions where Vo1d / BadBox live | **Yes — most important** |
| `userdata` | App data | Yes |
| `frp` | Factory Reset Protection (Google) | Yes |

**One partition the wipe does NOT touch**: the BootROM itself, which lives in
the SoC silicon. Maskrom mode (section 1) lives there. There is no software
that can rewrite or disable it.

**Verification command after Armbian boot**:
```bash
# All partitions should be standard Armbian layout (mmcblk1p1 boot, mmcblk1p2 root)
sudo lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,LABEL,FSTYPE
# No 'system', 'vendor', 'recovery', 'misc', 'frp' labels should appear.
# If they do, the flash was incomplete — wipe with 'sudo dd if=/dev/zero of=/dev/mmcblk1 bs=4M count=64' and re-flash.
```

---

## 5. Post-flash verification checklist

Run on the Armbian-booted RK3229 immediately after first boot, before
connecting it to any production network. All checks should return clean.

```bash
# 5.1 — No Android partition labels survive
sudo lsblk -o NAME,LABEL,FSTYPE | grep -Ei 'system|vendor|recovery|misc|frp|oem|trust' && echo "FAIL: Android partition survived" || echo "OK: clean partition table"

# 5.2 — No Vo1d-style debuggerd substitution (only meaningful if rootfs reuses /system path; Armbian doesn't, but check anyway)
[[ -e /system/bin/debuggerd ]] && echo "WARN: /system path exists on Armbian (unexpected)" || echo "OK: no /system path"

# 5.3 — No outbound to known BadBox / Vo1d C2s in DNS resolver cache or active sessions
ss -tnp 2>/dev/null | grep -Ei 'catmore88|ycxrl|duoduodev|flyermobi|motiyu|qazwsxedc' && echo "FAIL: C2 connection observed" || echo "OK: no known C2 traffic"

# 5.4 — Network traffic baseline (run before installing OpenBox stack)
sudo timeout 60 tcpdump -nn -i "$(ip route show default | awk '{print $5; exit}')" -c 200 not arp and not stp and not '(udp port 5353)' > /tmp/baseline.pcap 2>&1
# Inspect /tmp/baseline.pcap for unexpected outbound destinations.

# 5.5 — Firmware origin sanity
cat /etc/armbian-release 2>/dev/null | head -10
# Should show BOARD=rk322x-box and an official Armbian build date.

# 5.6 — Kernel modules from clean source (no out-of-tree shanzhai blobs)
find /lib/modules/$(uname -r) -name '*.ko*' | xargs -I{} basename {} .ko | sort -u | grep -Eiv '^(rockchip|rk_|sun[0-9]+|brcm|rtl|mt[0-9]+|ath|cfg80211|mac80211|usb|nft|ip|sch|cls|wireguard|cake|fou|fou6|ipt|xt|nf|crypto|aes|sha|gcm|chacha|poly|ext4|fat|vfat|nls_|usbcore|hid|input|drm|gpu|i2c|spi|uart|tty|serial|loop|md|raid|btrfs|f2fs|squashfs|fuse|nfs|cifs|isofs|cdrom|sd|mmc|scsi|sr|dm|tun|tap|veth|bridge|vxlan|gre|geneve|bonding|8021q|gpio|pwm|leds|hwmon|thermal|cpufreq|cpuidle|power|reboot|rtc|wd|watchdog|snd|sound|video|media|v4l|uvc|alsa|sof|ac97|spdif|fb|backlight|panel|hdmi|edp|dp|mipi|dsi|csi|isp|cif|vpu|rga|iep|vdec|venc|jpeg|h264|h265|vp8|vp9|av1)$' && echo "WARN: unexpected modules" || echo "OK: only stock module families present"
```

---

## 6. FCC filings — public hardware documentation sources

The R29_5G_LP3 family is sold under multiple white-label brands; FCC IDs vary
per branded SKU. Direct FCC filings for "R29_5G_LP3" as a board name are
unlikely (the FCC catalogues finished products, not Shenzhen reference PCBs),
but the **MXQ Pro 4K** product family that uses this board has FCC submissions
under various Chinese filer IDs.

**Public technical documentation (community-sourced, no FCC required)**:
- **Rockchip RK3229 datasheet V1.2** (rockchip.fr archive) — pin map, power
  sequencing, electrical specs.
- **MattWestb/R29-MXQ-LP3-V2.3-00908** (GitHub) — full board teardown for
  V2.3 revision: device tree files, GPIO map, power rails, eMMC layout.
- **CNX Software MXQ 4K teardown (2016-03-07)** — RK3229 reference design
  internals: NANYA `NT5CB256M16CP-D1` DRAM, Pulse `H1102NL` Ethernet
  magnetics, **Espressif ESP8089** Wi-Fi (NOT Realtek), unpopulated 3-pin
  serial console header on the PCB.
- **XDA / FreakTab / LibreELEC forums** — firmware archives for V1.1, V1.2,
  V2.3, V3.0 PCB revisions; useful for cross-referencing your unit's silkscreen
  ID with known DTS files.

**Why FCC filings are not the primary source here**: the FCC database catalogues
RF certification for the *finished branded product* (e.g., a specific MXQ TV
box SKU sold in the US). The R29_5G_LP3 PCB is a generic OEM design used inside
hundreds of branded SKUs, often sold under brands that never filed with the
FCC at all (units sold direct from Aliexpress to non-US buyers bypass FCC). Your
specific unit may have no FCC ID. The community teardowns and the GitHub repo
above are higher-signal sources for this PCB family.

---

## 7. FBI / FOIA material

The most relevant FBI document is **IC3 PSA250605** (2025-06-05) — a public
service announcement, not a FOIA-released file. It covers BadBox 2.0 generally
without naming specific SoCs or PCB revisions. Highlights:

- Confirms "supply chain compromise" as the primary infection vector.
- Recommends: monitor home network IoT traffic, avoid unofficial app stores,
  keep firmware updated.
- Does **not** publish IoCs (FBI PSAs typically don't; security vendors do).

A FOIA sweep for "Rockchip" / "Android TV box" / "shanzhai" returned no
specific declassified material at vault.fbi.gov as of this writing. The FBI's
public threat communication on this device class is contained in the IC3 PSA
above; substantive technical detail comes from HUMAN, Trend Micro, Bitsight,
and Doctor Web.

---

## 8. Operational summary — defensive checklist for the user

1. **Do not power-on the box on any network until it is wiped.** First-boot OTA
   is one of BadBox 2.0's three infection vectors.
2. **Enter maskrom mode** by shorting the documented PCB pad while plugging
   USB-OTG to a development host. Use `rkdeveloptool` to flash Armbian
   `rk322x-box`. Reference the GitHub teardown for the maskrom pad location on
   your specific PCB revision (V1.1 / V1.2 / V2.3 / V3.0).
3. **Run `tools/fingerprint-rk3229.sh`** on first Armbian boot to capture
   ground truth into `docs/hw/r29_5g_lp3.txt`.
4. **Run section 5 verification** above before connecting the unit to your
   production network.
5. **Then run `sudo ./install.sh`** to deploy OpenBox v0.2.0.
6. **Treat physical access as game-over** — maskrom mode cannot be disabled.

---

## 9. Sources

- FBI IC3 PSA250605 — `https://www.ic3.gov/PSA/2025/PSA250605`
- FBI Cyber Alert mirror — `https://www.fbi.gov/investigate/cyber/alerts/2025/home-internet-connected-devices-facilitate-criminal-activity`
- HUMAN Security Satori — BadBox 2.0 disruption — `https://www.humansecurity.com/learn/blog/satori-threat-intelligence-disruption-badbox-2-0/`
- Bitsight — BADBOX Botnet Is Back — `https://www.bitsight.com/blog/badbox-botnet-back`
- The Hacker News — Vo1d malware coverage — `https://thehackernews.com/2024/09/beware-new-vo1d-malware-infects-13.html`
- Krebs on Security — Android TV streaming box botnet — `https://krebsonsecurity.com/2025/11/is-your-android-tv-streaming-box-part-of-a-botnet/`
- Rockchip wiki — partition table — `https://opensource.rock-chips.com/wiki_Partitions`
- Rockchip wiki — maskrom — `http://rockchip.wikidot.com/how-to-enter-rockusb-maskrom-mode`
- MXQ 4K RK3229 teardown (CNX Software) — `https://www.cnx-software.com/2016/03/07/mxq-4k-rockchip-rk3229-android-tv-box-unboxing-and-teardown/`
- R29-MXQ-LP3-V2.3 teardown repo — `https://github.com/MattWestb/R29-MXQ-LP3-V2.3-00908`
- RK3229 datasheet V1.2 — `https://rockchip.fr/RK3229%20datasheet%20V1.2.pdf`
- Google blog — BadBox 2.0 lawsuit (Jul 2025) — `https://blog.google/innovation-and-ai/technology/safety-security/google-taking-legal-action-against-the-badbox-20-botnet/`
- Armbian community forum — RK3229 long story — `https://forum.armbian.com/topic/12401-long-story-linux-on-rk3229-rockchip/`
