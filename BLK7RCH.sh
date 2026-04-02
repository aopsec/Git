#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_NAME="$(basename "$0")"
MNT_ROOT="/mnt"
readonly EXIT_USAGE=2
readonly EXIT_PRECONDITION=3
readonly EXIT_DEPENDENCY=4
readonly EXIT_VALIDATION=5
readonly EXIT_RUNTIME=6

# Required variable names per spec
DISK=""
EFI_PART=""
LUKS_PART=""
LUKS_NAME="cryptlvm"
VG_NAME="vg"
LV_ROOT="lvroot"
LV_SWAP="lvswap"
LV_HOME="lvhome"

HOSTNAME=""
USERNAME=""
TIMEZONE="UTC"
WIFI_BACKEND="nm"
ALLOW_SSH_INBOUND="false"
ENABLE_BLACKARCH="true"
YES_MODE="false"
GLOBAL_DRY_RUN="false"
BLACKARCH_VERIFY_MODE="remote-sha256"
IDS_HOME_NET="[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
IDS_ENABLE_SERVICES="true"
SKIP_FULL_UPGRADE="false"
PACMAN_UPGRADED_ONCE="false"
IDS_MODE="minimal-local"
IDS_SNORT_PROFILE="balanced"
IDS_SUPPRESS_FILE=""
RUN_ID="$(date +%Y%m%d%H%M%S)"
INSTALL_YUM_COMPAT="true"

declare -a LOCALES=("en_US.UTF-8")

log_info() { printf '[INFO] %s\n' "$*"; }
log_warn() { printf '[WARN] %s\n' "$*"; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }

usage() {
  cat <<USAGE
Usage:
  ${SCRIPT_NAME} <subcommand> [options]

Subcommands:
  core-install         Full base install with encrypted LUKS+LVM
  workstation-profile  Install workstation packages and Hyprland template
  ids-profile          Install IDS profile (snort + suricata)
  validate             Validate resulting installation in /mnt
  dry-run              Run core-install workflow in dry-run mode

Required flags for core-install:
  --disk /dev/sdX|/dev/nvme0n1
  --hostname <name>
  --username <name>

Optional flags:
  --timezone <Area/City>          Default: UTC
  --locale <locale>               Repeatable (e.g., en_US.UTF-8)
  --wifi-backend nm|nm-iwd        Default: nm
  --allow-ssh-inbound true|false  Default: false
  --enable-blackarch true|false   Default: false
  --target-root /mnt              Default: /mnt
  --blackarch-verify remote-sha256|disabled  Default: remote-sha256
  --ids-home-net <cidr-list>      Default: [192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]
  --ids-enable-services true|false Default: true
  --skip-full-upgrade true|false   Default: false
  --ids-mode minimal-local|managed-rules Default: minimal-local
  --ids-snort-profile strict|balanced Default: balanced
  --ids-suppress-file /path/to/file Optional file copied to /etc/snort/suppress.conf
  --install-yum-compat true|false  Default: false (installs dnf and /usr/bin/yum symlink)
  --yes                            Skip destructive confirmation
  --dry-run                        Print actions without changing system
USAGE
}

run_cmd() {
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] $*"
    return 0
  fi
  "$@"
}

append_transaction_log() {
  local message="$1"
  local log_path="${MNT_ROOT}/var/log/blk7rch-install.log"
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] transaction-log: $message"
    return 0
  fi
  mkdir -p "${MNT_ROOT}/var/log"
  printf '%s run_id=%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$RUN_ID" "$message" >> "$log_path"
}

chroot_pacman_install() {
  local mode
  local -a packages=("$@")
  mode="full-upgrade"
  if [[ "$SKIP_FULL_UPGRADE" == "true" ]]; then
    mode="install-only"
  fi
  log_info "Pacman transaction mode=${mode} packages=${packages[*]}"
  append_transaction_log "mode=${mode} packages=${packages[*]}"

  if [[ "$SKIP_FULL_UPGRADE" == "false" && "$PACMAN_UPGRADED_ONCE" == "false" ]]; then
    run_cmd arch-chroot "$MNT_ROOT" pacman -Syyu --noconfirm
    PACMAN_UPGRADED_ONCE="true"
  fi
  run_cmd arch-chroot "$MNT_ROOT" pacman -S --needed --noconfirm "${packages[@]}"
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    log_error "Must run as root in Arch ISO environment."
    exit "$EXIT_PRECONDITION"
  fi
}

require_uefi() {
  if [[ ! -d /sys/firmware/efi ]]; then
    log_error "UEFI mode is required: /sys/firmware/efi was not found."
    exit "$EXIT_PRECONDITION"
  fi
}

require_arch_iso_context() {
  if [[ ! -x /usr/bin/pacstrap ]]; then
    log_error "Arch ISO environment required: pacstrap not found at /usr/bin/pacstrap."
    exit "$EXIT_PRECONDITION"
  fi
}

check_dependencies() {
  local -a deps=(
    "sgdisk:partition GPT and create EFI/LUKS layout"
    "cryptsetup:create and open LUKS2 container"
    "pvcreate:create LVM physical volume inside LUKS"
    "vgcreate:create LVM volume group"
    "lvcreate:create root/swap/home logical volumes"
    "mkfs.fat:format EFI partition as FAT32"
    "mkfs.ext4:format root and home filesystems"
    "mkswap:initialize swap logical volume"
    "mount:mount target filesystems under /mnt"
    "swapon:enable swap logical volume"
    "pacstrap:install Arch base system"
    "genfstab:generate fstab"
    "arch-chroot:execute system configuration in target"
    "grub-install:install GRUB bootloader"
    "grub-mkconfig:generate GRUB configuration"
    "mkinitcpio:build initramfs with encrypt+lvm2 hooks"
    "blkid:derive LUKS UUID for kernel cmdline"
    "sed:edit config files deterministically"
    "awk:validate and inspect generated config"
    "curl:download remote bootstrap and checksum files"
    "sha256sum:verify downloaded scripts against expected digest"
  )

  local entry cmd why
  for entry in "${deps[@]}"; do
    cmd="${entry%%:*}"
    why="${entry#*:}"
    if ! command -v "$cmd" >/dev/null 2>&1; then
      log_error "Missing dependency '$cmd' (needed to ${why})."
      exit "$EXIT_DEPENDENCY"
    fi
    log_info "Dependency OK: $cmd (${why})"
  done
}

parse_bool() {
  local value="$1"
  if [[ "$value" == "true" || "$value" == "false" ]]; then
    printf '%s' "$value"
  else
    log_error "Invalid boolean value '$value'. Use true|false."
    exit "$EXIT_USAGE"
  fi
}

validate_timezone() {
  if [[ ! -f "/usr/share/zoneinfo/${TIMEZONE}" ]]; then
    log_error "Invalid timezone '${TIMEZONE}': /usr/share/zoneinfo/${TIMEZONE} not found."
    exit "$EXIT_VALIDATION"
  fi
}

validate_locales() {
  local loc
  for loc in "${LOCALES[@]}"; do
    if [[ ! "$loc" =~ ^[A-Za-z_]+\.[A-Za-z0-9-]+$ ]]; then
      log_error "Invalid locale '${loc}'. Expected format like en_US.UTF-8."
      exit "$EXIT_VALIDATION"
    fi
  done
}

validate_disk() {
  if [[ -z "$DISK" ]]; then
    log_error "Missing required --disk argument."
    exit "$EXIT_USAGE"
  fi
  if [[ ! -b "$DISK" ]]; then
    log_error "Invalid disk '${DISK}': block device does not exist."
    exit "$EXIT_VALIDATION"
  fi
}

resolve_partition_paths() {
  if [[ "$DISK" =~ (nvme|mmcblk) ]]; then
    EFI_PART="${DISK}p1"
    LUKS_PART="${DISK}p2"
  else
    EFI_PART="${DISK}1"
    LUKS_PART="${DISK}2"
  fi
  log_info "Resolved partition paths: EFI_PART=${EFI_PART}, LUKS_PART=${LUKS_PART}"
}

confirm_destructive() {
  if [[ "$YES_MODE" == "true" || "$GLOBAL_DRY_RUN" == "true" ]]; then
    return 0
  fi
  log_warn "About to erase all data on ${DISK}."
  read -r -p "Type 'ERASE' to continue: " answer
  if [[ "$answer" != "ERASE" ]]; then
    log_error "Destructive action not confirmed. Aborting."
    exit "$EXIT_PRECONDITION"
  fi
}

prompt_luks_passphrase() {
  local p1 p2
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] skipping secure LUKS passphrase prompt"
    return 0
  fi

  read -r -s -p "Enter new LUKS passphrase: " p1
  printf '\n'
  read -r -s -p "Confirm new LUKS passphrase: " p2
  printf '\n'
  if [[ -z "$p1" || "$p1" != "$p2" ]]; then
    log_error "LUKS passphrase mismatch or empty input."
    exit "$EXIT_VALIDATION"
  fi
  LUKS_PASSPHRASE="$p1"
  unset p1 p2
}

partition_disk() {
  log_info "Partitioning ${DISK} with GPT (EFI + LUKS)."
  run_cmd sgdisk --zap-all "$DISK"
  run_cmd sgdisk -n 1:1MiB:+512MiB -t 1:ef00 -c 1:"EFI" "$DISK"
  run_cmd sgdisk -n 2:0:0 -t 2:8309 -c 2:"CRYPTLVM" "$DISK"

  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    if [[ ! -b "$EFI_PART" || ! -b "$LUKS_PART" ]]; then
      log_error "Partition creation failed: expected ${EFI_PART} and ${LUKS_PART}."
      exit "$EXIT_RUNTIME"
    fi
  fi
}

setup_encryption_lvm() {
  log_info "Creating LUKS2 container and LVM stack."
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    run_cmd cryptsetup luksFormat --type luks2 "$LUKS_PART"
    run_cmd cryptsetup open "$LUKS_PART" "$LUKS_NAME"
  else
    if [[ -z "${LUKS_PASSPHRASE:-}" ]]; then
      log_error "Internal error: missing LUKS passphrase in non-dry-run mode."
      exit "$EXIT_RUNTIME"
    fi
    printf '%s' "$LUKS_PASSPHRASE" | cryptsetup luksFormat --type luks2 "$LUKS_PART" -
    printf '%s' "$LUKS_PASSPHRASE" | cryptsetup open "$LUKS_PART" "$LUKS_NAME" -
    unset LUKS_PASSPHRASE
  fi

  run_cmd pvcreate "/dev/mapper/${LUKS_NAME}"
  run_cmd vgcreate "$VG_NAME" "/dev/mapper/${LUKS_NAME}"
  run_cmd lvcreate -L 8G -n "$LV_SWAP" "$VG_NAME"
  run_cmd lvcreate -L 50G -n "$LV_ROOT" "$VG_NAME"
  run_cmd lvcreate -l 100%FREE -n "$LV_HOME" "$VG_NAME"
}

format_and_mount() {
  log_info "Formatting and mounting filesystems."
  run_cmd mkfs.fat -F32 "$EFI_PART"
  run_cmd mkfs.ext4 "/dev/${VG_NAME}/${LV_ROOT}"
  run_cmd mkfs.ext4 "/dev/${VG_NAME}/${LV_HOME}"
  run_cmd mkswap "/dev/${VG_NAME}/${LV_SWAP}"

  run_cmd mkdir -p "$MNT_ROOT"
  run_cmd mount "/dev/${VG_NAME}/${LV_ROOT}" "$MNT_ROOT"
  run_cmd mkdir -p "$MNT_ROOT/home" "$MNT_ROOT/boot"
  run_cmd mount "/dev/${VG_NAME}/${LV_HOME}" "$MNT_ROOT/home"
  run_cmd mount "$EFI_PART" "$MNT_ROOT/boot"
  run_cmd swapon "/dev/${VG_NAME}/${LV_SWAP}"

  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    if [[ ! -d "$MNT_ROOT/boot" ]]; then
      log_error "Mount validation failed: $MNT_ROOT/boot does not exist."
      exit "$EXIT_RUNTIME"
    fi
  fi
}

install_base() {
  log_info "Installing base packages with pacstrap."
  local -a base_pkgs=(
    base linux linux-firmware lvm2 cryptsetup grub efibootmgr
    networkmanager sudo vim git mkinitcpio
    ufw wireguard-tools openvpn
  )

  run_cmd pacstrap "$MNT_ROOT" "${base_pkgs[@]}"
  append_transaction_log "pacstrap-packages=${base_pkgs[*]}"
  run_cmd genfstab -U "$MNT_ROOT"

  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    genfstab -U "$MNT_ROOT" >> "$MNT_ROOT/etc/fstab"
  else
    log_info "[dry-run] would append genfstab output to $MNT_ROOT/etc/fstab"
  fi
}

write_chroot_script() {
  local chroot_script="$MNT_ROOT/root/t440s_chroot_setup.sh"
  local locale_csv=""
  local idx
  for idx in "${!LOCALES[@]}"; do
    if [[ "$idx" -gt 0 ]]; then
      locale_csv+=","
    fi
    locale_csv+="${LOCALES[$idx]}"
  done

  cat > "$chroot_script" <<CHROOT
#!/usr/bin/env bash
set -euo pipefail

HOSTNAME="${HOSTNAME}"
USERNAME="${USERNAME}"
TIMEZONE="${TIMEZONE}"
WIFI_BACKEND="${WIFI_BACKEND}"
ALLOW_SSH_INBOUND="${ALLOW_SSH_INBOUND}"
LUKS_PART="${LUKS_PART}"
LUKS_NAME="${LUKS_NAME}"
VG_NAME="${VG_NAME}"
LV_ROOT="${LV_ROOT}"
LOCALES_CSV="${locale_csv}"

ln -sf "/usr/share/zoneinfo/\${TIMEZONE}" /etc/localtime
hwclock --systohc

IFS=',' read -r -a LOCALES <<< "\${LOCALES_CSV}"
for loc in "\${LOCALES[@]}"; do
  if ! grep -qE "^#?\${loc}[[:space:]]+UTF-8" /etc/locale.gen; then
    echo "\${loc} UTF-8" >> /etc/locale.gen
  fi
  sed -i "s|^#\(${loc}[[:space:]]\\+UTF-8\)|\1|" /etc/locale.gen
done
locale-gen
printf 'LANG=%s\n' "\${LOCALES[0]}" > /etc/locale.conf

echo "\$HOSTNAME" > /etc/hostname
cat > /etc/hosts <<EOFH
127.0.0.1 localhost
::1       localhost
127.0.1.1 \$HOSTNAME.localdomain \$HOSTNAME
EOFH

sed -i 's/^HOOKS=.*/HOOKS=(base udev autodetect modconf kms keyboard keymap consolefont block encrypt lvm2 filesystems fsck)/' /etc/mkinitcpio.conf
mkinitcpio -P

luks_uuid="\$(blkid -s UUID -o value "\$LUKS_PART")"
if [[ -z "\$luks_uuid" ]]; then
  echo "[ERROR] Failed to determine LUKS UUID for \$LUKS_PART" >&2
  exit 1
fi

sed -i "s|^GRUB_CMDLINE_LINUX=.*|GRUB_CMDLINE_LINUX=\\\"cryptdevice=UUID=\${luks_uuid}:\${LUKS_NAME} root=/dev/\${VG_NAME}/\${LV_ROOT}\\\"|" /etc/default/grub
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg

systemctl enable NetworkManager
if [[ "\$WIFI_BACKEND" == "nm-iwd" ]]; then
  mkdir -p /etc/NetworkManager/conf.d
  cat > /etc/NetworkManager/conf.d/wifi_backend.conf <<EOFW
[device]
wifi.backend=iwd
EOFW
fi

if ! id -u "\$USERNAME" >/dev/null 2>&1; then
  useradd -m -G wheel -s /bin/bash "\$USERNAME"
fi
echo '%wheel ALL=(ALL:ALL) ALL' > /etc/sudoers.d/10-wheel
chmod 0440 /etc/sudoers.d/10-wheel

ufw default deny incoming
ufw default allow outgoing
if [[ "\$ALLOW_SSH_INBOUND" == "true" ]]; then
  ufw allow ssh
fi
ufw --force enable
CHROOT

  chmod 0700 "$chroot_script"
}

configure_chroot() {
  log_info "Configuring installed system in chroot."
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    run_cmd arch-chroot "$MNT_ROOT" /bin/bash /root/t440s_chroot_setup.sh
    return
  fi

  write_chroot_script
  arch-chroot "$MNT_ROOT" /bin/bash /root/t440s_chroot_setup.sh
  rm -f "$MNT_ROOT/root/t440s_chroot_setup.sh"
}

configure_blackarch() {
  if [[ "$ENABLE_BLACKARCH" != "true" ]]; then
    log_info "BlackArch feature disabled."
    return 0
  fi

  log_info "BlackArch requested: performing integrity-checked bootstrap."
  local strap="${MNT_ROOT}/root/strap.sh"
  local strap_sha_file="${MNT_ROOT}/root/strap.sh.sha256"
  run_cmd curl -fsSL -o "$strap" https://blackarch.org/strap.sh
  if [[ "$BLACKARCH_VERIFY_MODE" == "remote-sha256" ]]; then
    run_cmd curl -fsSL -o "$strap_sha_file" https://blackarch.org/strap.sh.sha256
  fi

  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] would verify BlackArch strap checksum using ${BLACKARCH_VERIFY_MODE}."
    return 0
  fi

  if [[ ! -f "$strap" ]]; then
    log_error "BlackArch bootstrap script download failed: $strap not found."
    exit "$EXIT_RUNTIME"
  fi

  if [[ "$BLACKARCH_VERIFY_MODE" == "remote-sha256" ]]; then
    if [[ ! -f "$strap_sha_file" ]]; then
      log_error "BlackArch checksum file download failed: $strap_sha_file not found."
      exit "$EXIT_RUNTIME"
    fi
    local expected_sha
    local actual_sha
    expected_sha="$(awk '{print $1}' "$strap_sha_file")"
    actual_sha="$(sha256sum "$strap" | awk '{print $1}')"
    if [[ -z "$expected_sha" ]]; then
      log_error "BlackArch checksum file did not contain a valid SHA256 digest."
      exit "$EXIT_RUNTIME"
    fi
    if [[ "$actual_sha" != "$expected_sha" ]]; then
      log_error "BlackArch integrity check failed: expected ${expected_sha}, got ${actual_sha}."
      log_error "Aborting due to bootstrap integrity failure."
      exit "$EXIT_RUNTIME"
    fi
  elif [[ "$BLACKARCH_VERIFY_MODE" == "disabled" ]]; then
    log_warn "BlackArch checksum verification disabled by user choice."
  fi

  chmod +x "$strap"
  arch-chroot "$MNT_ROOT" /bin/bash /root/strap.sh
}

install_yum_compat() {
  if [[ "$INSTALL_YUM_COMPAT" != "true" ]]; then
    return 0
  fi
  log_info "Installing yum compatibility (dnf + yum symlink)."
  chroot_pacman_install dnf
  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    run_cmd arch-chroot "$MNT_ROOT" ln -sf /usr/bin/dnf /usr/bin/yum
    append_transaction_log "installed-yum-compat=true"
  else
    log_info "[dry-run] would symlink /usr/bin/yum to /usr/bin/dnf"
  fi
}

install_workstation_profile() {
  log_info "Installing workstation profile packages and Hyprland config."
  require_target_root_ready
  if [[ -z "$USERNAME" ]]; then
    log_error "workstation-profile requires --username."
    exit "$EXIT_USAGE"
  fi
  local -a ws_pkgs=(
    hyprland waybar foot wofi mako
    xdg-desktop-portal xdg-desktop-portal-hyprland xdg-desktop-portal-gtk
    xorg-xwayland brightnessctl wl-clipboard
  )

  chroot_pacman_install "${ws_pkgs[@]}"

  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    local target_dir="$MNT_ROOT/home/$USERNAME/.config/hypr"
    if [[ ! -d "$MNT_ROOT/home/$USERNAME" ]]; then
      log_error "User home '$MNT_ROOT/home/$USERNAME' missing. Ensure user exists in target system first."
      exit "$EXIT_PRECONDITION"
    fi
    mkdir -p "$target_dir"
    cat > "$target_dir/hyprland.conf" <<'EOFH'
# Minimal known-good Hyprland config written by installer
monitor=,preferred,auto,1
exec-once=waybar
exec-once=mako
input {
  kb_layout=us
}
general {
  gaps_in=5
  gaps_out=10
  border_size=2
}
bind=SUPER,Return,exec,foot
bind=SUPER,D,exec,wofi --show drun
bind=SUPER,Q,killactive
bind=SUPER,M,exit
EOFH
    chown -R "$USERNAME:$USERNAME" "$MNT_ROOT/home/$USERNAME/.config"
  else
    log_info "[dry-run] would create /home/$USERNAME/.config/hypr/hyprland.conf"
  fi
}

install_ids_profile() {
  log_info "Installing IDS profile (Snort + Suricata tuned for low false positives)."
  require_target_root_ready
  chroot_pacman_install snort suricata suricata-update

  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    local snort_dir="$MNT_ROOT/etc/snort"
    local suricata_dir="$MNT_ROOT/etc/suricata"
    local snort_profile_log="$MNT_ROOT/var/log/snort/profile-selection.log"
    local suricata_profile_log="$MNT_ROOT/var/log/suricata/profile-selection.log"

    mkdir -p "$snort_dir/rules" "$suricata_dir/rules"
    install -d -m 0750 "$MNT_ROOT/var/log/snort" "$MNT_ROOT/var/log/suricata"

    cat > "$snort_dir/threshold.conf" <<'EOF_SNORTTH'
# Snort threshold controls to reduce noisy repeats
event_filter gen_id 1, sig_id 1000001, type limit, track by_src, count 1, seconds 60
event_filter gen_id 1, sig_id 1000002, type limit, track by_src, count 1, seconds 30
EOF_SNORTTH

    if [[ -n "$IDS_SUPPRESS_FILE" ]]; then
      if [[ ! -f "$IDS_SUPPRESS_FILE" ]]; then
        log_error "Provided --ids-suppress-file '$IDS_SUPPRESS_FILE' not found."
        exit "$EXIT_VALIDATION"
      fi
      cp "$IDS_SUPPRESS_FILE" "$snort_dir/suppress.conf"
    else
      cat > "$snort_dir/suppress.conf" <<'EOF_SNORTSUP'
# Default suppressions; keep minimal to avoid hiding true positives.
# suppress gen_id 1, sig_id 2000001, track by_src, ip 10.0.0.0/8
EOF_SNORTSUP
    fi

    cat > "$snort_dir/snort.conf" <<EOF_SNORT
# Precision-focused Snort IDS profile generated by ${SCRIPT_NAME}
# Keeps the ruleset intentionally minimal to reduce false positives.
var HOME_NET ${IDS_HOME_NET}
var EXTERNAL_NET !\$HOME_NET
config policy_mode: tap
config alert_with_interface_name
output alert_fast: /var/log/snort/alert.fast
include /etc/snort/threshold.conf
include /etc/snort/suppress.conf
include /etc/snort/rules/local.rules
EOF_SNORT

    cat > "$snort_dir/rules/local.rules" <<'EOF_SNORTRULES'
# High-confidence local policy examples (keep rules narrow for precision)
alert tcp any any -> $HOME_NET 22 (msg:"SNORT high-confidence SSH brute-force pattern"; flow:to_server,established; detection_filter:track by_src, count 12, seconds 60; sid:1000001; rev:1;)
alert icmp any any -> $HOME_NET any (msg:"SNORT possible ICMP flood"; itype:8; detection_filter:track by_src, count 80, seconds 10; sid:1000002; rev:1;)
EOF_SNORTRULES

    if [[ "$IDS_SNORT_PROFILE" == "strict" ]]; then
      cat >> "$snort_dir/rules/local.rules" <<'EOF_SNORTSTRICT'
alert tcp any any -> $HOME_NET 3389 (msg:"SNORT strict RDP brute-force pattern"; flow:to_server,established; detection_filter:track by_src, count 10, seconds 60; sid:1000003; rev:1;)
EOF_SNORTSTRICT
    fi

    cat > "$suricata_dir/suricata.yaml" <<EOF_SURICATA
%YAML 1.1
---
vars:
  address-groups:
    HOME_NET: "${IDS_HOME_NET}"
    EXTERNAL_NET: "!\\$HOME_NET"
default-rule-path: /etc/suricata/rules
threshold-file: /etc/suricata/threshold.config
rule-files:
  - local.rules
af-packet:
  - interface: default
    cluster-id: 99
    cluster-type: cluster_flow
    defrag: yes
    use-mmap: yes
    tpacket-v3: yes
outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: /var/log/suricata/eve.json
      types:
        - alert:
            payload: no
            packet: no
            metadata: yes
            tagged-packets: no
  - fast:
      enabled: yes
      filename: /var/log/suricata/fast.log
EOF_SURICATA

    cat > "$suricata_dir/rules/local.rules" <<'EOF_SURIRULES'
# High-confidence local policy examples (precision over volume)
alert ssh any any -> $HOME_NET any (msg:"SURICATA possible SSH brute force"; flow:to_server,established; threshold:type both, track by_src, count 12, seconds 60; sid:2100001; rev:1;)
alert icmp any any -> $HOME_NET any (msg:"SURICATA possible ICMP flood"; itype:8; threshold:type both, track by_src, count 80, seconds 10; sid:2100002; rev:1;)
EOF_SURIRULES
    cat > "$suricata_dir/threshold.config" <<'EOF_SURITH'
threshold gen_id 1, sig_id 2100001, type both, track by_src, count 1, seconds 60
threshold gen_id 1, sig_id 2100002, type both, track by_src, count 1, seconds 30
EOF_SURITH

    if [[ "$IDS_MODE" == "managed-rules" ]]; then
      cat > "$suricata_dir/enable.conf" <<'EOF_SURIENABLE'
emerging-scan.rules
emerging-dos.rules
EOF_SURIENABLE

      cat > "$suricata_dir/disable.conf" <<'EOF_SURIDISABLE'
re:.*policy.*
re:.*chat.*
re:.*games.*
EOF_SURIDISABLE

      run_cmd arch-chroot "$MNT_ROOT" suricata-update \
        --suricata-conf /etc/suricata/suricata.yaml \
        --enable-conf /etc/suricata/enable.conf \
        --disable-conf /etc/suricata/disable.conf
      {
        echo "run_id=${RUN_ID}"
        echo "ids_mode=${IDS_MODE}"
        echo "enabled_rules_file=/etc/suricata/enable.conf"
        echo "disabled_rules_file=/etc/suricata/disable.conf"
      } > "$suricata_profile_log"
    else
      {
        echo "run_id=${RUN_ID}"
        echo "ids_mode=${IDS_MODE}"
        echo "local_rules_only=true"
      } > "$suricata_profile_log"
    fi

    run_cmd arch-chroot "$MNT_ROOT" snort -T -c /etc/snort/snort.conf
    run_cmd arch-chroot "$MNT_ROOT" suricata -T -c /etc/suricata/suricata.yaml -v
    {
      echo "run_id=${RUN_ID}"
      echo "snort_profile=${IDS_SNORT_PROFILE}"
      echo "suppress_file=/etc/snort/suppress.conf"
      echo "threshold_file=/etc/snort/threshold.conf"
    } > "$snort_profile_log"
    append_transaction_log "ids-mode=${IDS_MODE} snort-profile=${IDS_SNORT_PROFILE}"
    if [[ "$IDS_ENABLE_SERVICES" == "true" ]]; then
      run_cmd arch-chroot "$MNT_ROOT" systemctl enable snort.service suricata.service
    fi
  else
    log_info "[dry-run] would install precision-tuned Snort and Suricata configs and validate with -T."
  fi
}

run_validation() {
  log_info "Running installation validation checks."
  require_target_root_ready
  local ok=true

  if [[ ! -f "$MNT_ROOT/etc/fstab" ]]; then
    log_error "Validation failed: $MNT_ROOT/etc/fstab missing."
    ok=false
  fi

  if [[ ! -f "$MNT_ROOT/etc/default/grub" ]]; then
    log_error "Validation failed: $MNT_ROOT/etc/default/grub missing."
    ok=false
  elif ! awk '/^GRUB_CMDLINE_LINUX=/{found=1} END{exit(found?0:1)}' "$MNT_ROOT/etc/default/grub"; then
    log_error "Validation failed: GRUB_CMDLINE_LINUX not set."
    ok=false
  fi

  if [[ "$WIFI_BACKEND" == "nm-iwd" && ! -f "$MNT_ROOT/etc/NetworkManager/conf.d/wifi_backend.conf" ]]; then
    log_error "Validation failed: nm-iwd selected but wifi_backend.conf missing."
    ok=false
  fi

  if [[ -d "$MNT_ROOT/home/$USERNAME/.config/hypr" && ! -f "$MNT_ROOT/home/$USERNAME/.config/hypr/hyprland.conf" ]]; then
    log_error "Validation failed: Hyprland config directory exists but hyprland.conf missing."
    ok=false
  fi

  if [[ -f "$MNT_ROOT/etc/snort/snort.conf" ]]; then
    if ! awk '/include \/etc\/snort\/rules\/local.rules/{found=1} END{exit(found?0:1)}' "$MNT_ROOT/etc/snort/snort.conf"; then
      log_error "Validation failed: snort.conf missing local.rules include."
      ok=false
    fi
    if ! awk '/include \/etc\/snort\/threshold.conf/{t=1} /include \/etc\/snort\/suppress.conf/{s=1} END{exit(t&&s?0:1)}' "$MNT_ROOT/etc/snort/snort.conf"; then
      log_error "Validation failed: snort.conf missing threshold/suppress includes."
      ok=false
    fi
  fi

  if [[ -f "$MNT_ROOT/etc/suricata/suricata.yaml" ]]; then
    if ! awk '/rule-files:/{rf=1} /- local.rules/{lr=1} END{exit(rf&&lr?0:1)}' "$MNT_ROOT/etc/suricata/suricata.yaml"; then
      log_error "Validation failed: suricata.yaml must include local.rules for precision profile."
      ok=false
    fi
    if ! awk '/threshold-file:/{tf=1} END{exit(tf?0:1)}' "$MNT_ROOT/etc/suricata/suricata.yaml"; then
      log_error "Validation failed: suricata.yaml missing threshold-file declaration."
      ok=false
    fi
  fi

  if [[ ! -f "$MNT_ROOT/var/log/blk7rch-install.log" ]]; then
    log_error "Validation failed: transaction log $MNT_ROOT/var/log/blk7rch-install.log missing."
    ok=false
  fi

  if [[ "$ok" == "false" ]]; then
    exit "$EXIT_VALIDATION"
  fi
  log_info "Validation succeeded."
}

parse_common_flags() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --disk) DISK="${2:-}"; shift 2 ;;
      --hostname) HOSTNAME="${2:-}"; shift 2 ;;
      --username) USERNAME="${2:-}"; shift 2 ;;
      --timezone) TIMEZONE="${2:-}"; shift 2 ;;
      --locale) LOCALES+=("${2:-}"); shift 2 ;;
      --wifi-backend)
        WIFI_BACKEND="${2:-}"
        if [[ "$WIFI_BACKEND" != "nm" && "$WIFI_BACKEND" != "nm-iwd" ]]; then
          log_error "Invalid --wifi-backend '${WIFI_BACKEND}'. Use nm|nm-iwd."
          exit "$EXIT_USAGE"
        fi
        shift 2
        ;;
      --allow-ssh-inbound)
        ALLOW_SSH_INBOUND="$(parse_bool "${2:-}")"
        shift 2
        ;;
      --enable-blackarch)
        ENABLE_BLACKARCH="$(parse_bool "${2:-}")"
        shift 2
        ;;
      --target-root)
        MNT_ROOT="${2:-}"
        shift 2
        ;;
      --blackarch-verify)
        BLACKARCH_VERIFY_MODE="${2:-}"
        if [[ "$BLACKARCH_VERIFY_MODE" != "remote-sha256" && "$BLACKARCH_VERIFY_MODE" != "disabled" ]]; then
          log_error "Invalid --blackarch-verify '${BLACKARCH_VERIFY_MODE}'. Use remote-sha256|disabled."
          exit "$EXIT_USAGE"
        fi
        shift 2
        ;;
      --ids-home-net)
        IDS_HOME_NET="${2:-}"
        shift 2
        ;;
      --ids-enable-services)
        IDS_ENABLE_SERVICES="$(parse_bool "${2:-}")"
        shift 2
        ;;
      --skip-full-upgrade)
        SKIP_FULL_UPGRADE="$(parse_bool "${2:-}")"
        shift 2
        ;;
      --ids-mode)
        IDS_MODE="${2:-}"
        if [[ "$IDS_MODE" != "minimal-local" && "$IDS_MODE" != "managed-rules" ]]; then
          log_error "Invalid --ids-mode '${IDS_MODE}'. Use minimal-local|managed-rules."
          exit "$EXIT_USAGE"
        fi
        shift 2
        ;;
      --ids-snort-profile)
        IDS_SNORT_PROFILE="${2:-}"
        if [[ "$IDS_SNORT_PROFILE" != "strict" && "$IDS_SNORT_PROFILE" != "balanced" ]]; then
          log_error "Invalid --ids-snort-profile '${IDS_SNORT_PROFILE}'. Use strict|balanced."
          exit "$EXIT_USAGE"
        fi
        shift 2
        ;;
      --ids-suppress-file)
        IDS_SUPPRESS_FILE="${2:-}"
        shift 2
        ;;
      --install-yum-compat)
        INSTALL_YUM_COMPAT="$(parse_bool "${2:-}")"
        shift 2
        ;;
      --yes)
        YES_MODE="true"
        shift
        ;;
      --dry-run)
        GLOBAL_DRY_RUN="true"
        shift
        ;;
      *)
        log_error "Unknown argument: $1"
        usage
        exit "$EXIT_USAGE"
        ;;
    esac
  done
}

validate_required_args() {
  if [[ -z "$HOSTNAME" ]]; then
    log_error "Missing required --hostname argument."
    exit "$EXIT_USAGE"
  fi
  if [[ -z "$USERNAME" ]]; then
    log_error "Missing required --username argument."
    exit "$EXIT_USAGE"
  fi
}

require_target_root_ready() {
  if [[ ! -d "$MNT_ROOT" ]]; then
    log_error "Target root '$MNT_ROOT' does not exist."
    exit "$EXIT_PRECONDITION"
  fi
  if [[ ! -f "$MNT_ROOT/etc/os-release" ]]; then
    log_error "Target root '$MNT_ROOT' is not a bootstrapped Linux system (/etc/os-release missing). Run core-install first."
    exit "$EXIT_PRECONDITION"
  fi
}

core_install() {
  validate_required_args
  validate_timezone
  validate_locales

  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    if [[ -z "$DISK" ]]; then
      log_error "Missing required --disk argument."
      exit "$EXIT_USAGE"
    fi
    resolve_partition_paths
    log_info "Dry-run mode: skipping root/UEFI/dependency/block-device enforcement."
  else
    require_root
    require_uefi
    require_arch_iso_context
    check_dependencies
    validate_disk
    resolve_partition_paths
    confirm_destructive
    prompt_luks_passphrase
  fi

  partition_disk
  setup_encryption_lvm
  format_and_mount
  install_base
  configure_chroot
  install_yum_compat
  configure_blackarch
  log_info "Core installation completed successfully."
}

main() {
  if [[ $# -lt 1 ]]; then
    usage
    exit "$EXIT_USAGE"
  fi

  local subcommand="$1"
  shift

  case "$subcommand" in
    core-install)
      parse_common_flags "$@"
      core_install
      ;;
    workstation-profile)
      parse_common_flags "$@"
      require_root
      validate_required_args
      install_workstation_profile
      ;;
    ids-profile)
      parse_common_flags "$@"
      require_root
      install_ids_profile
      ;;
    validate)
      parse_common_flags "$@"
      run_validation
      ;;
    dry-run)
      GLOBAL_DRY_RUN="true"
      parse_common_flags "$@"
      core_install
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      log_error "Unknown subcommand: $subcommand"
      usage
      exit "$EXIT_USAGE"
      ;;
  esac
}

main "$@"
