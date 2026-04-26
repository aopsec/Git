# Inside the MXQ Pro 5G 4K R2390: a Rockchip clone with a malware problem

The MXQ Pro 5G 4K box marketed under build **R2390 / Android 8.1 / 2020.06.15** is, with high confidence, a **Rockchip RK3229 (or pin-compatible RK3228A) reference design** wearing the generic Shenzhen "R29_5G_LP3" PCB family — a 32-bit quad-Cortex-A7 chip with Mali-400 graphics, typically 1 GB DDR3 / 8 GB eMMC, and **no genuine 5 GHz Wi-Fi or Bluetooth on most batches** despite the marketing. More importantly, this exact model name appears on **HUMAN Security's, Google's, and the FBI's confirmed BadBox / BadBox 2.0 infected-device list** (FBI PSA I-060525-PSA, June 2025) — the firmware ships with a Triada-derived backdoor that survives factory reset. Treat the device as compromised by default; this report documents the architecture so you can analyse, isolate, or repurpose it, not so you can put it on a trusted network.

The "5G" branding refers to **5 GHz Wi-Fi**, not cellular. The "MXQ Pro 5G 4K" label is unbranded white-label and has been applied to at least four different SoC families (Rockchip RK3229/RK3228A, Rockchip RK3128, Allwinner H3/H313, Amlogic S905W). The build-ID prefix "R2390" — together with Rockchip's distinctive "R29x"/"R329Q" board-naming convention seen across XDA, FreakTab, and LibreELEC threads — fingerprints this unit as the RK3229 variant. Definitive confirmation requires opening the case and reading the chip silkscreen, but flashing-tool, partition layout, kernel version, and firmware-archive evidence all agree.

## SoC, CPU, GPU, and the no-PMIC reference design

**Rockchip RK3229** (28 nm) drives the box: four ARM **Cortex-A7 cores at ~1.5 GHz, 32-bit ARMv7-A only** (vendor 64-bit claims are false), paired with a **Mali-400 MP2** GPU (vendors quote "penta-core" by counting the geometry processor). Real-world Antutu scores cluster around 12,000–19,000, with thermal throttling on sustained 10-bit HEVC. RK3228A is pin-compatible and functionally identical from a user perspective — distinguishable only by removing the heatsink.

A defining trait of this platform is that **there is no power-management IC**. Rockchip designed the RK3229 to allow an ultra-low BOM, so the PCB uses **discrete buck converters** (typically generic SY8113B, MP2143, SY8089, or EUP3458 in SOT-23/SOT-89 packages) plus a couple of LDOs. The RK808/RK809-class PMICs are reserved for RK3288/RK3328/RK3399 boards. There is **no battery, no fuel gauge, no RTC backup**, which is why these boxes lose the clock when unplugged.

## Memory, storage, and the fake-capacity epidemic

Genuine SKUs ship with **1 GB DDR3 (entry) or 2 GB DDR3 (uprated)**, usually four discrete chips such as Nanya NT5CB256M16CP-D1 or Samsung K4B2G0446C, occasionally consolidated in an eMCP package like Kingston 08EMCP08. Storage is **8 GB or 16 GB eMMC** — typical parts include SanDisk SDIN8DE4-8G, SK Hynix H26M42003GMR, and Samsung KLM8G1GETF / Foresee NCEMBSF9. A microSD slot supports cards up to roughly 32 GB reliably.

**Any listing claiming 4/32 GB, 8/64 GB, or 16/256 GB on this chassis is almost certainly fraudulent**. XDA users repeatedly report build.prop values forged in firmware to misrepresent capacity; the only ground truth is `cat /proc/meminfo` and `cat /proc/partitions` over ADB. This fraud is endemic across the entire MXQ Pro clone class.

## Wireless, Ethernet, and ports — the "5G" lie

The Wi-Fi/Bluetooth module is the **single most variable component** between batches sold under this exact name. Documented chipsets on R29_5G_LP3 boards include **SSV6051P / SV6051P** (single-band 2.4 GHz only — most common), **Realtek RTL8189FTV/ES** (single-band, no BT), **Espressif ESP8089/ESP8285** (cheapest, 2.4 GHz only), **Realtek RTL8723BS** (2.4 GHz + BT 4.0), **Broadcom AP6255** (genuine dual-band + BT, premium SKU), and **SC9012P** (genuine dual-band). On the SSV6051P, RTL8189, and ESP8089 batches, **5 GHz Wi-Fi simply does not function and Bluetooth is absent entirely**, despite both being printed on the box. Only AP6255 and SC9012P units honour the "5G" marketing.

Ethernet is **10/100 Mbps Fast Ethernet** with no external PHY chip — the RK3229 integrates the PHY, leaving only Pulse H1102NL (or equivalent) magnetics on the PCB next to the RJ-45. **HDMI is 2.0a** with HDCP 2.2, supporting **4K @ 60 Hz at 4:2:0 8-bit** with a quality cable; 4K @ 30 Hz is the practical default. HDR10 is listed in the datasheet but rarely usable in practice; **Dolby Vision and AV1 are absent**. The four USB-A ports are **USB 2.0 native to the SoC** (no hub IC), with one doubling as the OTG flashing port. A 3.5 mm AV jack carries composite + stereo audio and usually hides the recessed reset button; coaxial S/PDIF, IR receiver, and a 5 V / 2 A barrel jack complete the I/O.

## The video pipeline: 4K HEVC works, the rest is marketing

The RK3229's hardware decoder handles **H.265/HEVC Main and Main10 up to 4K @ 60 fps and ~200 Mbps**, **H.264 up to 4K @ 30 fps**, **VP9 Profile 0/2 up to 4K @ 60**, plus MPEG-1/2/4, VC-1, VP8, and 1080p AVS+. There is **no AV1 hardware decode** and **no Dolby Vision** path. HDR10 metadata pass-through is unreliable. CNX Software's 2016 review noted that high-bitrate 10-bit content stutters not because the decoder fails, but because the Cortex-A7 cores throttle thermally — so the practical 4K ceiling is 50–80 Mbps depending on the cooling pad inside the case.

## Android 8.1 Oreo, full edition, on Linux 4.4

The OS is **Android 8.1.0 Oreo, full edition** — not Android Go, despite the 1 GB RAM constraint. The Rockchip RK322x BSP simply ships AOSP TV unmodified, even on devices that struggle to run it (FreakTab/XDA users widely report lag and overheating). The kernel is **Linux 4.4.x** (the RK322x Android 8.1 BSP standard; the older Android 7.x builds on the same hardware used 3.10.x). Build fingerprints in this family typically read `rk322x_box-userdebug/test-keys` — the userdebug + test-keys combination is itself a security red flag because it leaves `ro.debuggable=1` and accepts any community-signed OTA package.

## Boot chain and the Rockchip partition fingerprint

The boot sequence runs **BootROM → idbloader.img (Rockchip miniloader / Boot1) → uboot.img (U-Boot 2014.10-RK322X, Rockchip fork) → trust.img (OP-TEE TEE-CORE 1.0.1) → boot.img or recovery.img**. The miniloader initialises DDR3, hands off to U-Boot at 0x60000000, which reads `parameter.txt` and the `misc` boot-control block before jumping to the Android boot image. The partition table is the smoking gun for SoC identification — Amlogic uses `tee/rsv/factory/dtb/logo`, Allwinner uses `boot0/boot-resource`, but the RK3229 layout on rk29xxnand is unmistakable:

| Partition | Size (sectors) | Role |
|---|---|---|
| uboot | 0x2000 | Rockchip U-Boot fork |
| trust | 0x4000 | OP-TEE TrustZone image |
| misc | 0x2000 | Boot Control Block |
| baseparamer | 0x800 | HDMI/display parameters |
| resource | 0x7800 | Boot logo + DTB |
| kernel | 0x6000 | zImage with KRNL header |
| boot | 0xC000 | Android ramdisk |
| recovery | 0x10000 | Recovery image |
| backup, cache, metadata, kpanic | various | Rockchip-specific |
| system | 0x400000 | ~1 GB Android system |
| userdata | remainder | User data |

The presence of `baseparamer`, `resource`, `kernel` (separate from `boot`), `backup`, and `kpanic` is uniquely Rockchip — that alone confirms the SoC family without opening the case.

## Flashing, firmware sources, and a dead OTA server

The toolchain is exclusively Rockchip's: **RKDevTool / AndroidTool v2.58+, Rockchip Batch Tool v1.8, Factory Tool v1.64, SD_Firmware_Tool**, plus the Linux `rkdeveloptool` and `upgrade_tool`. The driver is **Rockchip DriverAssistant** with the device enumerating as **VID 0x2207 / PID 0x320b** in MaskROM mode — entered by holding the recessed reset button (inside the AV jack) while connecting USB OTG, or by shorting the eMMC clock pin on bricks. The image format is a single `update.img` containing AFP-Tool packed components (extract with `afptool -unpack update.img`).

The exact "R2390 / 2020.06.15" firmware **is not publicly archived** — this is a per-batch OEM build. The closest siblings available are **R329Q_V3.2 (Android 7.1.2, NV5.20180816)** on FreakTab, **R29_5G_LP3_V1.2_00523** referenced on XDA, and the **R329Q_V8.0** Android 8.0 dump (~773 MB) on Androidnovo. The built-in "Wireless Update" / "OTA Update" app pulls an `update.zip` (Rockchip OTA package format containing MiniLoaderAll.bin, parameter.txt, kernel.img, boot.img, recovery.img, system.img, trust.img, uboot.img, misc.img, package-file, RESERVED) from a hardcoded OEM URL — but the server is **dead in the wild**, generating ubiquitous "Check Failed! Check Your OTA Server" errors. Extracting the URL would require decompiling the `UpgradeSys` or `Wireless Update` APK from `/system/app`. Useful sources include FreakTab's RK3229 firmware-ROMs-tools sub-forum, AndroidPCtv, the Internet Archive's "Android TV 8.1 Oreo ROM for RK3229 with SV6051" community build, ilmich's unofficial **LibreELEC RK322x builds** (mainline kernel 6.x), Armbian's RK322x port (legacy 4.4 needed for SSV6X5X Wi-Fi), and the open-source **jhswartz/rk3229 GitHub repo** (full U-Boot + OP-TEE + Linux).

## Root, ADB, and a bootloader that was never locked

The device is **almost certainly pre-rooted** — `userdebug/test-keys` builds in this family routinely ship with SuperSU preinstalled in `/system/xbin/su`; running `su` in a terminal app frequently just works. **ADB-over-network on TCP 5555 is often enabled by default** in `default.prop` even when the developer-options UI hides it; try `adb connect <ip>:5555` blind. If a UI toggle exists, it lives behind the standard seven-tap-build-number gesture. For stubborn cases, mounting `/system` rw and adding `ro.adb.secure=0`, `ro.secure=0`, `ro.debuggable=1`, `persist.service.adb.enable=1` to `/system/build.prop` plus the same in the boot.img ramdisk's `default.prop` (repacked with magiskboot) is the canonical recipe.

The bootloader is effectively unlocked by design — there is no `fastboot oem unlock` flow because Rockchip's chain-of-trust is optional and disabled in the consumer reference firmware. Any unsigned `update.img` flashes via RKDevTool in MaskROM mode. The UART debug header lives on the PCB (typically a 3- or 4-pin pad near the SoC or AV jack), runs at **115200 8N1, 3.3 V logic**, and drops to a U-Boot prompt on key-press during boot — and to an unauthenticated root Android shell after boot on userdebug builds. **Do not connect VCC** on a USB-TTL adapter; share only GND/TX/RX and power the box from its own PSU. CH340, CP2102, and FT232 adapters all work. Note that some 2020-era MXQ Pro 4K 5G batches **physically depopulate the AV-jack reset button** to lock users into stock — in that case eMMC pin-shorting or `adb reboot recovery` are the only recovery routes.

## The malware problem you cannot ignore

This is the most consequential finding in the entire research, and it changes how the device should be handled.

**The "MXQ Pro 5G" appears by name in HUMAN Security's October 2023 BadBox report** alongside T95, T95Z, T95MAX, X88, Q9, X12PLUS, and the J5-W tablet — eight devices confirmed shipping with a Triada-derived firmware backdoor. The "MXQ9PRO" variant appears on the **BadBox 2.0 list** that drove the **FBI's June 5, 2025 public service announcement (PSA I-060525-PSA)** and Google's July 2025 federal lawsuit (S.D.N.Y. Case 1:25-CV-04503-JPO). HUMAN and Google count over **one million infected devices across 222 countries** as of March 2025. The malware contacts a Chinese C2 on first boot, downloads stage-2 payloads, and participates in residential-proxy botnet activity, ad fraud, fake-account creation, and credential stuffing — and because it lives in the boot partition, **factory reset does not remove it**.

A second, independent threat documented by Dr.Web in 2023 — **Android.Pandora**, a Mirai variant — propagates through this device class via either malicious OTA updates signed with leaked Android test-keys (note: MXQ Pro builds carry `test-keys` fingerprints, making them eligible) or via pirated streaming apps such as youcine, magistv, and unitv. Pandora drops `gomediad.so` and `GoMediaService`, opens a **privileged shell on TCP port 4521**, and unleashes TCP/UDP/SYN/ICMP/DNS-flood DDoS capability. Its persistence files (`pandoraspearrk`, `supervisord`, `daemonsu`, `preinstall.sh`) are injected into the boot ramdisk.

Layered atop the deliberate backdoors is an Android 8.1 base **frozen at the 2018 patch level** — Stagefright, BlueBorne, Janus, Magellan, and dozens of other RCEs are unmitigated. There are no MXQ-specific CVEs because the white-label vendor cannot be assigned one, but the attack surface is extreme.

The FBI, Google, and HUMAN's collective recommendation is unambiguous: **disconnect the device from the network**. If the box is to be kept, isolate it on a guest VLAN with no LAN access, assume any credential typed into it is exfiltrated, and consider reflashing to **CoreELEC, LibreELEC, or Armbian** — the Rockchip RK322x has community ports that overwrite the entire system partition and largely neutralise the firmware-resident threat (though boot-partition implants survive a `system`-only reflash; do a full `update.img` flash via RKDevTool to be safe).

## Conclusion: a $25 BOM, an open bootloader, and a permanent backdoor

The MXQ Pro 5G 4K R2390 is a textbook example of why the cheap-Android-TV-box category is a security disaster. The hardware itself is competent for the price — RK3229 with 4K HEVC decode, gigabit-class HDMI 2.0, four native USB ports, and an integrated Ethernet PHY all on a no-PMIC discrete-regulator design that hits an extraordinary BOM target. The architecture is also unusually transparent for hackers: an unlocked bootloader, a 115200-baud UART pad on the PCB, a `userdebug/test-keys` Android build, ADB-over-IP on by default, and a fully documented Rockchip flashing toolchain make this one of the easiest devices in existence to take apart and reflash.

That same openness is what makes the device dangerous in its stock state. The vendor's "Wireless Update" path is a one-way trust channel to a server that is either dead or hostile, the firmware is signed with publicly leaked test-keys, and **the device's name is on the FBI's BadBox advisory**. The right mental model is not "cheap Android box" but "tamper-friendly ARM development kit that ships pre-owned by a botnet." Treat the R2390 as a learning platform — flash LibreELEC or Armbian, enjoy the open UART, study the Rockchip boot chain — but do not let the stock firmware touch a network you care about.