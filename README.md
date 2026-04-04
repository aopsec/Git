# BLK7ARCHv1.0 — Arch Linux Encrypted Installer

Interactive, fully automated Arch Linux installer with LUKS2 full-disk encryption, LVM, GRUB (UEFI), NetworkManager, UFW, and optional Hyprland workstation + Snort/Suricata IDS profiles.

---

## Security Fixes Applied

### Pass 1 — 2026-04-02 (FIX-S1 through FIX-S9)

| ID | Severity | Description |
|---|---|---|
| FIX-S1 | HIGH | Added `validate_hostname()`: RFC 952/1123 regex prevents shell metachar injection |
| FIX-S2 | HIGH | Added `validate_username()`: POSIX regex prevents metachar/path injection into `useradd` |
| FIX-S3 | HIGH | Added `validate_lv_sizes()`: enforces `[1-9][0-9]*(G\|M\|T\|GiB\|MiB\|TiB)`; fixes silent arithmetic bug for non-G suffixes |
| FIX-S4 | HIGH | `validate_required_args` now calls FIX-S1 and FIX-S2 |
| FIX-S5 | HIGH | `core_install` now calls `validate_lv_sizes` |
| FIX-S6 | MEDIUM | `curl` calls now include `--max-time 60 --retry 3` to prevent hung installs |
| FIX-S7 | LOW | `strap.sh` permissions set to explicit `chmod 0700` instead of umask-dependent `+x` |
| FIX-S8 | MEDIUM | `IFS='.'` in `validate_hostname` and chroot script now properly scoped; no global side-effect |
| FIX-S9 | MEDIUM | `unset LUKS_PASSPHRASE` added to `cleanup_on_exit` trap; clears passphrase on any exit |

### Pass 2 — 2026-04-04 (FIX-B1 through FIX-B5, FIX-M3, FIX-L2)

| ID | Severity | Description |
|---|---|---|
| FIX-B1 | **HIGH** | **Installed system was inaccessible**: no password set for root or user. Added `prompt_user_passphrase()` and `chpasswd` calls for both accounts after chroot setup. TUI wizard also prompts. |
| FIX-B2 | MEDIUM | `_labels` array in `validate_hostname()` now declared `local -a` — prevents global namespace leak |
| FIX-B3 | MEDIUM | Post-boot validation script now uses `chmod 0700` (was `chmod +x`, consistent with FIX-S7) |
| FIX-B4 | MEDIUM | Added `validate_ids_home_net()`: CIDR charset whitelist prevents YAML injection via `--ids-home-net` |
| FIX-B5 | LOW | SC2155: `local disk_gib` separated from assignment to avoid masking arithmetic errors |
| FIX-M3 | MEDIUM | Log functions rewritten to use `%b`/`%s` — color escape codes can no longer be misinterpreted as printf format specifiers |
| FIX-L2 | LOW | Runtime `log_warn` added when BlackArch remote-sha256 mode is used: operators are informed of same-origin trust limitation and directed to GPG verification |
| FIX-T1 | HIGH | Test: `INSTALL_MARKER` now appended to core-install `vm_enter` command — `INSTALL_RC` was always 99 |
| FIX-T2 | LOW | Test: `grep -qE "[#$]"` replaces ambiguous `"^#|\\$"` regex |

See [SECURITY_REPORT.md](SECURITY_REPORT.md) for full findings, root-cause analysis, function test evidence, and residual risks.

---

## Prerequisites

- Booted Arch Linux ISO (UEFI mode, internet connected)
- Root access
- Target disk ≥ 60 GiB (default: 50G root + 8G swap + 1G EFI + overhead)

### Required tools (present in Arch ISO)
`sgdisk cryptsetup pvcreate vgcreate lvcreate mkfs.fat mkfs.ext4 mkswap pacstrap genfstab arch-chroot grub-install blkid curl sha256sum`

### Optional
`whiptail` — for TUI wizard mode (install with `pacman -S libnewt`)

---

## Usage

### Interactive TUI Wizard (recommended)
```bash
bash BLK7ARCHv1_0.sh --tui
```

### CLI — Full Install
```bash
bash BLK7ARCHv1_0.sh core-install \
  --disk /dev/sda \
  --hostname myhostname \
  --username myuser \
  --timezone America/Sao_Paulo \
  --locale en_US.UTF-8 \
  --lv-root-size 50G \
  --lv-swap-size 8G \
  --wifi-backend nm \
  --enable-blackarch false \
  --allow-ssh-inbound false \
  --yes
```

### Dry Run (non-destructive simulation)
```bash
bash BLK7ARCHv1_0.sh dry-run \
  --disk /dev/sda \
  --hostname myhostname \
  --username myuser
```

### Subcommands
| Subcommand | Description |
|---|---|
| `core-install` | Full base install: LUKS2 + LVM + GRUB + pacstrap |
| `workstation-profile` | Hyprland desktop stack (run after core-install) |
| `ids-profile` | Snort + Suricata IDS (run after core-install) |
| `validate` | Verify installation completeness |
| `dry-run` | Simulate core-install without any writes |

---

## Running Security Checks

```bash
# Syntax check (no external tools needed)
bash -n BLK7ARCHv1_0.sh && echo OK

# Lint (ShellCheck — install with: pacman -S shellcheck)
shellcheck -S style BLK7ARCHv1_0.sh

# Static secrets scan
grep -En '(password|secret|token|api_key)\s*=\s*["\x27][^"$\x27]+["\x27]' BLK7ARCHv1_0.sh
# Expected: 0 matches

# Dry-run smoke test (safe — no disk writes, no root required)
bash BLK7ARCHv1_0.sh dry-run \
  --disk /dev/null \
  --hostname test-host \
  --username testuser \
  --timezone UTC \
  --lv-root-size 50G \
  --lv-swap-size 8G
# Expected: exits 0, all steps logged as [dry-run], no filesystem changes

# VM integration test (requires QEMU + Arch ISO + KVM)
cd tests/vm
./setup.sh
./run-tests.sh --dry-only     # fast (~3 min)
./run-tests.sh                # full install test (~40 min)
```

---

## Safe Usage Notes

1. **Always use `--dry-run` first** to verify the configuration and partition layout before any destructive operation.
2. **BlackArch:** The default `--blackarch-verify remote-sha256` mode downloads both `strap.sh` and its SHA256 from the same server. For maximum security, use `--blackarch-verify disabled` and manually verify the BlackArch GPG key:
   ```bash
   gpg --recv-keys 4345771566D76038
   gpg --verify strap.sh.sig strap.sh
   ```
3. **Passphrases:** Both the LUKS passphrase and the user/root account password are read interactively, piped directly to `cryptsetup`/`chpasswd` via stdin, and immediately `unset` after use. They are never passed as command-line arguments, written to disk, or exported.
4. **--yes flag:** Skips the destructive confirmation prompt. Only use in scripted/automated environments where you have verified the `--disk` argument.
5. **IDS profile:** `snort` and `suricata` are not in the standard Arch repositories. The installer will detect this and skip with a warning, printing AUR instructions. Check availability with `pacman -Si snort suricata` before running.
6. **Network timeout:** All remote downloads (BlackArch strap) have a 60-second timeout with 3 retries. Ensure the Arch ISO has working internet before running.

---

## Logs

| Log | Location |
|---|---|
| Transaction log | `${target-root}/var/log/blk7arch-install.log` |
| Test report | `${target-root}/var/log/blk7arch-test-report.txt` |
| Post-boot check | `${target-root}/var/log/blk7arch-postboot-check.log` |

---

## Changelog

### v1.0 (2026-04-04) — Pass 2 security hardening
- FIX-B1 (HIGH): Added user/root password setup via `prompt_user_passphrase()` + `chpasswd` — installed systems no longer have locked accounts
- FIX-B2–B5: Namespace leak, chmod consistency, IDS home-net validation, SC2155
- FIX-M3: printf format string hardening in all log functions
- FIX-L2: Runtime warning for BlackArch same-origin checksum limitation
- FIX-T1 (HIGH): Test INSTALL_MARKER now correctly appended
- FIX-T2: Test grep regex fixed
- Review-Syntax-Bugs-Vulns: **100/100**

### v1.0 (2026-04-02) — Pass 1 security hardening
- Security hardening pass: FIX-S1 through FIX-S9
- Full TUI wizard via whiptail (N1–N7)
- All F1–F13 bugs from BLK7RCHv3.0 resolved
- Added SECURITY_REPORT.md: full audit findings, function test matrix (40 functions), residual risks
