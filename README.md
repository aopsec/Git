# BLK7ARCHv1.0 — Arch Linux Encrypted Installer

Interactive, fully automated Arch Linux installer with LUKS2 full-disk encryption, LVM, GRUB (UEFI), NetworkManager, UFW, and optional Hyprland workstation + Snort/Suricata IDS profiles.

---

## Security Fixes Applied (Hardening Pass — 2026-04-02)

| ID | Severity | Description |
|---|---|---|
| FIX-S1 | HIGH | Added `validate_hostname()`: RFC 952/1123 regex prevents shell metachar injection into chroot script |
| FIX-S2 | HIGH | Added `validate_username()`: POSIX regex prevents shell metachar/path injection into useradd and chroot |
| FIX-S3 | HIGH | Added `validate_lv_sizes()`: enforces `[1-9][0-9]*(G\|M\|T\|GiB\|MiB\|TiB)` format; fixes silent arithmetic bug when non-G suffixes were used |
| FIX-S4 | HIGH | `validate_required_args` now calls FIX-S1 and FIX-S2 |
| FIX-S5 | HIGH | `core_install` now calls `validate_lv_sizes` |
| FIX-S6 | MEDIUM | `curl` calls now include `--max-time`/`--retry` to prevent hung installs |
| FIX-S7 | LOW | `strap.sh` permissions set to explicit `0700` instead of umask-dependent `+x` |

See `SECURITY_REPORT.md` for full findings, root-cause analysis, and residual risks.

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
# Lint (ShellCheck)
shellcheck -S style BLK7ARCHv1_0.sh

# Static secrets scan
grep -En '(password|secret|token|api_key)\s*=\s*["\x27][^"$\x27]+["\x27]' BLK7ARCHv1_0.sh

# Dry-run smoke test
bash BLK7ARCHv1_0.sh dry-run \
  --disk /dev/null \
  --hostname test-host \
  --username testuser \
  --lv-root-size 50G \
  --lv-swap-size 8G
# Expected: exits 0, all steps logged as [dry-run]
```

---

## Safe Usage Notes

1. **Always use `--dry-run` first** to verify the configuration and partition layout before any destructive operation.
2. **BlackArch:** The default `--blackarch-verify remote-sha256` mode downloads both `strap.sh` and its SHA256 from the same server. For maximum security, use `--blackarch-verify disabled` and manually verify the BlackArch GPG key:
   ```bash
   gpg --recv-keys 4345771566D76038
   gpg --verify strap.sh.sig strap.sh
   ```
3. **LUKS passphrase:** The passphrase is read interactively, piped directly to `cryptsetup`, and immediately `unset` from memory. It is never written to disk, logged, or exported.
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

### v1.0 (2026-04-02)
- Security hardening pass: FIX-S1 through FIX-S7
- Full TUI wizard via whiptail (N1–N7)
- All F1–F13 bugs from BLK7RCHv3.0 resolved
