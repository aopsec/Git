# BLK7RCHv3.0.sh — Arch Linux Encrypted Installer (T440s profile)

`BLK7RCHv3.0.sh` is a staged Bash installer for Arch Linux with:

- UEFI + GPT partitioning
- LUKS2 encrypted container + LVM (`root`, `home`, `swap`)
- GRUB encrypted boot configuration (`cryptdevice=UUID=...`)
- Optional workstation profile (Hyprland stack)
- Optional IDS profile (Snort + Suricata)
- Optional BlackArch bootstrap with checksum validation
- Dry-run mode for non-destructive simulation

---

## 1) Supported subcommands

- `core-install`
- `workstation-profile`
- `ids-profile`
- `validate`
- `dry-run`

---

## 2) Preconditions

You **must** run from Arch ISO/live environment as root.

Required conditions:

1. `EUID=0`
2. UEFI boot mode (`/sys/firmware/efi` exists)
3. Valid target block device (e.g. `/dev/sda`, `/dev/nvme0n1`)
4. Internet connectivity for package installation (and BlackArch if enabled)

> ⚠️ `core-install` is destructive: it repartitions the target disk.

---

## 3) Installation quick start

Make executable:

```bash
chmod +x BLK7RCHv3.0.sh
```

Recommended first run (non-destructive simulation):

```bash
./BLK7RCHv3.0.sh dry-run \
  --disk /dev/nvme0n1 \
  --hostname BLK7RCH \
  --username k450 \
  --timezone America/Sao_Paulo \
  --locale en_US.UTF-8 \
  --locale pt_BR.UTF-8 \
  --wifi-backend nm-iwd \
  --allow-ssh-inbound true
```

Real install:

```bash
./BLK7RCHv3.0.sh core-install \
  --disk /dev/nvme0n1 \
  --hostname BLK7RCH \
  --username k450 \
  --timezone America/Sao_Paulo \
  --locale en_US.UTF-8 \
  --locale pt_BR.UTF-8 \
  --wifi-backend nm-iwd \
  --allow-ssh-inbound true \
  --yes
```

During real install, the script prompts for the LUKS passphrase securely (`read -s`).

---

## 4) Full CLI flags

### Required for `core-install`

- `--disk /dev/sdX|/dev/nvme0n1`
- `--hostname <name>`
- `--username <name>`

### Optional

- `--timezone <Area/City>` (default: `America/Sao_Paulo`)
- `--locale <locale>` (repeatable)
- `--wifi-backend nm|nm-iwd` (default: `nm`)
- `--allow-ssh-inbound true|false` (default: `false`)
- `--enable-blackarch true|false` (default: `false`)
- `--blackarch-verify remote-sha256|disabled` (default: `remote-sha256`)
- `--target-root <path>` (default: `/mnt`)
- `--skip-full-upgrade true|false` (default: `false`)
- `--install-yum-compat true|false` (default: `false`)
- `--test-report true|false` (default: `false`, writes test/install status files)
- `--ids-home-net <cidr-list>`
- `--ids-enable-services true|false` (default: `true`)
- `--ids-mode minimal-local|managed-rules` (default: `minimal-local`)
- `--ids-snort-profile strict|balanced` (default: `balanced`)
- `--ids-suppress-file /path/to/file` (optional)
- `--yes`
- `--dry-run`

---

## 5) What `core-install` does

1. Validates root/UEFI/disk and required tools.
2. Resolves partition naming:
   - SATA/SCSI: `/dev/sda1`, `/dev/sda2`
   - NVMe/MMC: `/dev/nvme0n1p1`, `/dev/nvme0n1p2`
3. Creates GPT layout:
   - EFI (`+512MiB`)
   - LUKS partition (rest of disk)
4. Formats and opens LUKS2 container (`cryptlvm`).
5. Creates LVM VG/LVs (`vg/lvroot`, `vg/lvhome`, `vg/lvswap`).
6. Mounts filesystems under `--target-root` (default `/mnt`).
7. Installs base system with `pacstrap`.
8. Enters chroot and configures:
   - timezone, locales, hostname
   - `mkinitcpio` hooks with `encrypt` and `lvm2`
   - GRUB with encrypted kernel cmdline
   - NetworkManager (`nm` or `nm-iwd`)
   - user + sudoers
   - UFW defaults (deny inbound, allow outbound; SSH inbound optional)
9. Optional: installs yum compatibility (`dnf` + symlink).
10. Optional: BlackArch bootstrap with SHA256 verification.

---

## 6) Workstation profile

Install workstation packages (Hyprland + portals + tools) after base install:

```bash
./BLK7RCHv3.0.sh workstation-profile \
  --target-root /mnt \
  --hostname BLK7RCH \
  --username k450
```

Writes a known-good Hyprland config to:

- `/home/<username>/.config/hypr/hyprland.conf`

If the target user does not exist yet, the script auto-creates the user in chroot before writing config.

---

## 7) IDS profile

Install and configure Snort + Suricata:

```bash
./BLK7RCHv3.0.sh ids-profile \
  --target-root /mnt \
  --hostname BLK7RCH \
  --username k450 \
  --ids-mode managed-rules \
  --ids-snort-profile strict \
  --ids-home-net "[10.10.0.0/16]"
```

Behavior:

- Uses transactional package helper (`chroot_pacman_install`).
- Supports one-time full upgrade unless `--skip-full-upgrade true`.
- Generates Snort threshold/suppress configs.
- Supports Suricata managed rules (`enable.conf` / `disable.conf`) via `suricata-update`.
- If `suricata-update` is missing, script attempts to install `python-suricata-update` automatically.
- Runs `snort -T` and `suricata -T` config tests before enabling services.

---

## 8) Validation and logs

Validate installation state:

```bash
./BLK7RCHv3.0.sh validate \
  --target-root /mnt \
  --hostname BLK7RCH \
  --username k450
```

Important logs/files:

- Transaction log: `/var/log/blk7rch-install.log` (inside target root)
- Test report: `/var/log/blk7rch-test-report.txt` (inside target root when `--test-report true`)
- Snort profile log: `/var/log/snort/profile-selection.log`
- Suricata profile log: `/var/log/suricata/profile-selection.log`

When `--test-report true` is used with `core-install`, the installer enables a one-time post-boot validation service that writes:

- `/var/log/blk7rch-postboot-check.log`
- `/var/log/blk7rch-postboot-check.ok`

Use this to confirm boot-time checks after the first reboot.

---

## 9) Safety notes

- Always run `dry-run` before destructive installs.
- Double-check `--disk` target (wrong disk = data loss).
- Keep IDS rules conservative first, then tune based on real traffic.
- Do final production validation on real hardware and network traffic.

---

## 10) Example staged workflow

```bash
# 1) simulate
./BLK7RCHv3.0.sh dry-run --disk /dev/nvme0n1 --hostname BLK7RCH --username k450

# 2) install base
./BLK7RCHv3.0.sh core-install --disk /dev/nvme0n1 --hostname BLK7RCH --username k450 --yes

# 3) install workstation profile
./BLK7RCHv3.0.sh workstation-profile --target-root /mnt --hostname BLK7RCH --username k450

# 4) install IDS profile
./BLK7RCHv3.0.sh ids-profile --target-root /mnt --hostname BLK7RCH --username k450 --ids-mode minimal-local

# 5) validate
./BLK7RCHv3.0.sh validate --target-root /mnt --hostname BLK7RCH --username k450
```
