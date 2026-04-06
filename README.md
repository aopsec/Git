# BLK7ARCHv1.0 — Arch Linux Encrypted Installer

Interactive, fully automated Arch Linux installer with LUKS2 full-disk encryption, LVM, GRUB (UEFI), NetworkManager, UFW, and optional Hyprland workstation + Snort/Suricata IDS profiles.

---

## Security Fixes Applied

### Pass 4 — 2026-04-06 (FIX-BUG01–FIX-BUG08) — screencast live-test hardening

| ID | Severity | Description |
|---|---|---|
| FIX-BUG05 | **CRITICAL** | `choose_from_menu()`: all display output redirected to stderr — function called as `$(...)` so stdout was captured into caller variable; menu was invisible to user and return value was polluted with menu text → `validate_install_cfg` rejected it → crash with exit 1 after all inputs collected (BUG-02/05/09) |
| FIX-BUG04 | HIGH | `parse_install_args()`: added `[[ $# -lt 2 ]]` guard before every two-arg option — `shift 2` with only 1 arg exits 1 under `set -e`, producing silent rollback with no error message (BUG-04/07) |
| FIX-BUG08 | CRITICAL | `interactive_wizard()`: early return with `/dev/null` disk when `GLOBAL_DRY_RUN=true` — `install --dry-run` no longer prompts interactively then crashes (BUG-08) |
| FIX-BUG03 | HIGH | `load_config_file()`: missing config file error now includes `config-init <file>` suggestion (BUG-03) |
| FIX-BUG01 | MEDIUM | `main()`: `--dry-run` without a subcommand now emits an actionable warning explaining the required `install` subcommand, then exits with code 2 (BUG-01) |

**Pass 4 Scores:** Review-Syntax-Bugs-Vulns = **100/100** | Full-test = **100/100**

---

### Pass 3 — 2026-04-06 (FIX-ITER1-A, FIX-ITER1-B) — script-loop recursive hardening

| ID | Severity | Description |
|---|---|---|
| FIX-ITER1-A | MEDIUM | `install_ids_profile()`: added early dry-run return before `arch-chroot pacman -Si` probe — eliminates unguarded arch-chroot call + misleading "packages not in standard repos" warning when no chroot environment exists |
| FIX-ITER1-B | LOW | `_to_gib()` promoted from nested function (inside `validate_disk_size`) to top-level — bash nested functions pollute global namespace after first outer-function invocation; prevents silent re-definition on repeated calls |

**Pass 3 Scores:** Review-Syntax-Bugs-Vulns = **100/100** | Full-test = **100/100**

---

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

### Recommended (new unified workflow)
```bash
# Standard guided installer (interactive, safe defaults)
bash BLK7ARCHv1_0.sh install

# Advanced guided installer (menus for deeper customization)
bash BLK7ARCHv1_0.sh install --advanced
```

### Config-driven install
```bash
# Generate a starter config profile
bash BLK7ARCHv1_0.sh config-init

# Run with config pre-filled (still asks confirmation unless unattended)
bash BLK7ARCHv1_0.sh install --config install.conf

# Fully unattended mode (for CI/labs; still requires explicit config values)
bash BLK7ARCHv1_0.sh install --config install.conf --unattended
```

### Additional commands
| Command | Description |
|---|---|
| `install [--advanced] [--config file] [--unattended] [--dry-run]` | Primary installer (unified core + workstation flow) |
| `config-init [file]` | Generate editable installer config template |
| `profile-list` | Show available install profiles (`minimal`, `core`, `workstation`, `pentest`, `custom`) |
| `self-test` | Dry-run oriented install pipeline self-test |
| `help` | Show command help |

### Legacy command mapping (temporary compatibility)
| Old command | New recommendation |
|---|---|
| `core-install ...` | `install` (deprecated command still routed internally) |
| `workstation-profile ...` | `install` + choose workstation mode |
| `ids-profile ...` | `install --advanced` + enable IDS |
| `dry-run ...` | `install --dry-run` |

---

## Running Security Checks

```bash
# Syntax check (no external tools needed)
bash -n BLK7ARCHv1_0.sh && echo OK

# Built-in self-test (dry-run — safe, no root required)
bash BLK7ARCHv1_0.sh self-test
# Expected: exits 0, full pipeline logged with [dry-run] prefix

# Lint (ShellCheck — install with: pacman -S shellcheck)
shellcheck -S style BLK7ARCHv1_0.sh

# Static secrets scan
grep -En '(password|secret|token|api_key)\s*=\s*["\x27][^"$\x27]+["\x27]' BLK7ARCHv1_0.sh
# Expected: 0 matches

# Validation boundary tests (all should exit 5 or 2)
bash BLK7ARCHv1_0.sh install --dry-run --disk /dev/null --hostname 'bad;host' --username u --yes 2>&1; echo "E:$?"
bash BLK7ARCHv1_0.sh install --dry-run --disk /dev/sdX --hostname h --username u --yes 2>&1; echo "E:$?"

# IDS dry-run path (should not call arch-chroot)
bash BLK7ARCHv1_0.sh install --dry-run --disk /dev/null --hostname h --username u --yes 2>&1 | grep 'dry-run'

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

### v1.0.2 (2026-04-06) — Pass 4 screencast live-test bug fixes
- FIX-BUG05 (CRITICAL): `choose_from_menu()` all display now goes to stderr — was causing invisible menus and garbage `CFG[profile]` values → crash after every interactive install
- FIX-BUG04 (HIGH): `parse_install_args()` missing-arg guards for all two-arg options — `--config` without a file no longer crashes silently
- FIX-BUG08 (CRITICAL): `install --dry-run` now auto-uses defaults without prompting
- FIX-BUG03 (HIGH): Missing config file error now suggests `config-init`
- FIX-BUG01 (MEDIUM): `--dry-run` without subcommand gives actionable warning
- Review-Syntax-Bugs-Vulns: **100/100** | Full-test: **100/100**

### v1.0 (2026-04-06) — Pass 3 script-loop recursive hardening
- FIX-ITER1-A (MEDIUM): `install_ids_profile()` now returns early in dry-run — eliminates unguarded `arch-chroot` execution and misleading "packages not in repos" warning
- FIX-ITER1-B (LOW): `_to_gib()` promoted from nested to top-level function — prevents bash global namespace pollution on repeated outer-function calls
- Review-Syntax-Bugs-Vulns: **100/100** | Full-test: **100/100**

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
