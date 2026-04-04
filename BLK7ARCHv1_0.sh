#!/usr/bin/env bash
# ==============================================================================
# BLK7ARCHv1.0.sh — Interactive Arch Linux Encrypted Installer
# Successor to BLK7RCHv3.0 — Full TUI wizard + all bugs fixed
#
# Fixes from BLK7RCH.sh:
#   [F1]  SC2155: readonly SCRIPT_NAME now declared separately
#   [F2]  Chroot script name changed from t440s_chroot_setup.sh → blk7arch_chroot.sh
#   [F3]  ids-profile now calls validate_required_args
#   [F4]  Locale regex sanitized (fgrep/fixed-string) to prevent injection
#   [F5]  iwd package auto-included when --wifi-backend=nm-iwd
#   [F6]  genfstab: dry-run path no longer writes to real fstab
#   [F7]  GRUB EFI directory explicit at /boot (correct for UEFI+GPT layout)
#   [F8]  Disk size validation before lvcreate (checks ≥58 GiB available)
#   [F9]  Dry-run cryptsetup uses echo pipe, not interactive prompt
#   [F10] Cleanup/rollback trap closes LUKS and deactivates VG on failure
#   [F11] Locale dedup before processing
#   [F12] iwd.service enabled in chroot when nm-iwd selected
#   [F13] --locale dedup prevents duplicate locale.gen entries
#
# Security hardening pass (recursive loop v1):
#   [FIX-S1] validate_hostname: RFC 952/1123 regex — prevents shell metachar injection
#   [FIX-S2] validate_username: POSIX regex — prevents shell metachar/path injection
#   [FIX-S3] validate_lv_sizes: enforces numeric+suffix format, fixes disk_size arithmetic
#            for GiB/MiB/TiB units (previous code stripped only 'G', silently wrong)
#   [FIX-S4] validate_required_args now calls FIX-S1 + FIX-S2
#   [FIX-S5] core_install now calls validate_lv_sizes
#   [FIX-S6] curl calls get --max-time 60 + --retry 3 (prevents hung installs)
#   [FIX-S7] strap.sh permissions set to 0700 (not +x which is umask-dependent)
#
# New in v1.0:
#   [N1]  Full TUI wizard via whiptail (auto-detect + interactive prompts)
#   [N2]  Auto-disk discovery and menu
#   [N3]  LV size wizard with disk-size-aware validation
#   [N4]  Color-coded timestamped log output (INFO/WARN/ERROR/STEP)
#   [N5]  Cleanup trap on any ERR or EXIT
#   [N6]  --tui flag forces TUI even if flags present
#   [N7]  Profile summary screen before destructive execution
# ==============================================================================
set -euo pipefail

# [F1] SC2155 fix: declare and assign separately
SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME

readonly VERSION="1.0"
readonly EXIT_USAGE=2
readonly EXIT_PRECONDITION=3
readonly EXIT_DEPENDENCY=4
readonly EXIT_VALIDATION=5
readonly EXIT_RUNTIME=6

# --- Defaults -----------------------------------------------------------------
MNT_ROOT="/mnt"
DISK=""
EFI_PART=""
LUKS_PART=""
LUKS_NAME="cryptlvm"
VG_NAME="vg"
LV_ROOT="lvroot"
LV_SWAP="lvswap"
LV_HOME="lvhome"
LV_ROOT_SIZE="50G"
LV_SWAP_SIZE="8G"

HOSTNAME_VAL=""
USERNAME=""
TIMEZONE="America/Sao_Paulo"
WIFI_BACKEND="nm"
ALLOW_SSH_INBOUND="false"
ENABLE_BLACKARCH="false"
YES_MODE="false"
GLOBAL_DRY_RUN="false"
TUI_MODE="false"
BLACKARCH_VERIFY_MODE="remote-sha256"
IDS_HOME_NET="[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
IDS_ENABLE_SERVICES="true"
SKIP_FULL_UPGRADE="false"
PACMAN_UPGRADED_ONCE="false"
IDS_MODE="minimal-local"
IDS_SNORT_PROFILE="balanced"
IDS_SUPPRESS_FILE=""
INSTALL_YUM_COMPAT="false"
TEST_REPORT="false"
RUN_ID="$(date +%Y%m%d%H%M%S)"

declare -a LOCALES=("en_US.UTF-8")

# --- Color + Logging ----------------------------------------------------------
_BOLD="\033[1m"
_RST="\033[0m"
_CYAN="\033[0;36m"
_GREEN="\033[0;32m"
_YELLOW="\033[0;33m"
_RED="\033[0;31m"
_BLUE="\033[0;34m"

# [FIX-M3] Use %b for escape codes so color vars never act as format specifiers;
#           user-controlled $* is always isolated in a %s argument.
log_step()  { printf '%b[STEP]%b %s %s\n' "${_BOLD}${_BLUE}" "${_RST}" "$(date +%H:%M:%S)" "$*"; }
log_info()  { printf '%b[INFO]%b %s %s\n' "${_CYAN}"          "${_RST}" "$(date +%H:%M:%S)" "$*"; }
log_ok()    { printf '%b[ OK ]%b %s %s\n' "${_GREEN}"         "${_RST}" "$(date +%H:%M:%S)" "$*"; }
log_warn()  { printf '%b[WARN]%b %s %s\n' "${_YELLOW}"        "${_RST}" "$(date +%H:%M:%S)" "$*"; }
log_error() { printf '%b[ERR ]%b %s %s\n' "${_RED}"           "${_RST}" "$(date +%H:%M:%S)" "$*" >&2; }

# --- Rollback / Cleanup Trap [F10] -------------------------------------------
_CLEANUP_DONE="false"
cleanup_on_exit() {
  local exit_code="$?"
  [[ "$_CLEANUP_DONE" == "true" ]] && return
  _CLEANUP_DONE="true"
  unset LUKS_PASSPHRASE 2>/dev/null || true   # [FIX-S9] clear passphrase even on cryptsetup failure
  unset USER_PASSPHRASE 2>/dev/null || true   # [FIX-B1] clear user passphrase on any exit

  if [[ "$exit_code" -ne 0 && "$GLOBAL_DRY_RUN" == "false" ]]; then
    log_warn "Non-zero exit ($exit_code) — running rollback..."
    # Deactivate VG if active
    if vgdisplay "$VG_NAME" >/dev/null 2>&1; then
      vgchange -an "$VG_NAME" 2>/dev/null || true
      log_warn "Deactivated VG: $VG_NAME"
    fi
    # Close LUKS if open
    if [[ -b "/dev/mapper/${LUKS_NAME}" ]]; then
      cryptsetup close "$LUKS_NAME" 2>/dev/null || true
      log_warn "Closed LUKS mapper: $LUKS_NAME"
    fi
  fi
}
trap cleanup_on_exit EXIT

# --- Helpers ------------------------------------------------------------------
run_cmd() {
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] $*"
    return 0
  fi
  "$@"
}

append_transaction_log() {
  local message="$1"
  local log_path="${MNT_ROOT}/var/log/blk7arch-install.log"
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] transaction-log: $message"
    return 0
  fi
  mkdir -p "${MNT_ROOT}/var/log"
  printf '%s run_id=%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$RUN_ID" "$message" \
    >> "$log_path"
}

write_test_report() {
  local status_line="$1"
  local report_path="${MNT_ROOT}/var/log/blk7arch-test-report.txt"
  [[ "$TEST_REPORT" != "true" ]] && return 0
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] test-report: $status_line"
    return 0
  fi
  mkdir -p "${MNT_ROOT}/var/log"
  printf '%s run_id=%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$RUN_ID" "$status_line" \
    >> "$report_path"
}

# [F13] locale dedup helper
dedup_locales() {
  local -a seen=()
  local -a deduped=()
  local loc
  for loc in "${LOCALES[@]}"; do
    local already=false
    local s
    for s in "${seen[@]+"${seen[@]}"}"; do
      [[ "$s" == "$loc" ]] && already=true && break
    done
    if [[ "$already" == "false" ]]; then
      seen+=("$loc")
      deduped+=("$loc")
    fi
  done
  LOCALES=("${deduped[@]}")
}

# --- Dependency / Precondition checks ----------------------------------------
require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    log_error "Must run as root in Arch ISO environment."
    exit "$EXIT_PRECONDITION"
  fi
}

require_uefi() {
  if [[ ! -d /sys/firmware/efi ]]; then
    log_error "UEFI mode required: /sys/firmware/efi not found."
    exit "$EXIT_PRECONDITION"
  fi
}

require_arch_iso_context() {
  if [[ ! -x /usr/bin/pacstrap ]]; then
    log_error "Arch ISO required: pacstrap not found."
    exit "$EXIT_PRECONDITION"
  fi
}

check_dependencies() {
  local -a deps=(
    "sgdisk:partition GPT/EFI+LUKS layout"
    "cryptsetup:create/open LUKS2 container"
    "pvcreate:create LVM physical volume"
    "vgcreate:create LVM volume group"
    "lvcreate:create root/swap/home LVs"
    "mkfs.fat:format EFI as FAT32"
    "mkfs.ext4:format root and home"
    "mkswap:initialize swap"
    "mount:mount filesystems"
    "swapon:enable swap"
    "pacstrap:install Arch base"
    "genfstab:generate fstab"
    "arch-chroot:configure target"
    "grub-install:install GRUB bootloader"
    "grub-mkconfig:generate GRUB config"
    "mkinitcpio:build initramfs"
    "blkid:derive LUKS UUID"
    "sed:edit config files"
    "awk:inspect generated configs"
    "curl:download remote files"
    "sha256sum:verify checksums"
  )
  local entry cmd why
  for entry in "${deps[@]}"; do
    cmd="${entry%%:*}"
    why="${entry#*:}"
    if ! command -v "$cmd" >/dev/null 2>&1; then
      log_error "Missing dependency '$cmd' (needed to ${why})."
      exit "$EXIT_DEPENDENCY"
    fi
    log_info "Dependency OK: $cmd"
  done
}

parse_bool() {
  local value="$1"
  if [[ "$value" == "true" || "$value" == "false" ]]; then
    printf '%s' "$value"
  else
    log_error "Invalid boolean '$value'. Use true|false."
    exit "$EXIT_USAGE"
  fi
}

validate_timezone() {
  if [[ ! -f "/usr/share/zoneinfo/${TIMEZONE}" ]]; then
    log_error "Invalid timezone '${TIMEZONE}'."
    exit "$EXIT_VALIDATION"
  fi
}

validate_locales() {
  local loc
  for loc in "${LOCALES[@]}"; do
    if [[ ! "$loc" =~ ^[A-Za-z_]+\.[A-Za-z0-9-]+$ ]]; then
      log_error "Invalid locale '${loc}'. Expected format: en_US.UTF-8"
      exit "$EXIT_VALIDATION"
    fi
  done
}

# [FIX-S1] Validate hostname: RFC 952/1123 — labels 1-63 chars, alphanumeric + hyphens,
#           no leading/trailing hyphen, total ≤253 chars, no shell metacharacters.
validate_hostname() {
  if [[ -z "$HOSTNAME_VAL" ]]; then return 0; fi  # emptiness checked in validate_required_args
  local label_re='^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$'
  local full_re='^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$'
  if [[ ${#HOSTNAME_VAL} -gt 253 ]]; then
    log_error "Hostname '${HOSTNAME_VAL}' exceeds 253 characters."
    exit "$EXIT_VALIDATION"
  fi
  if [[ ! "$HOSTNAME_VAL" =~ $full_re ]]; then
    log_error "Invalid hostname '${HOSTNAME_VAL}'. Use only letters, digits, hyphens, and dots."
    exit "$EXIT_VALIDATION"
  fi
  # Each dot-separated label must also be individually valid
  local label
  local IFS='.'       # [FIX-S8] scope IFS change to avoid global word-split side-effect
  local -a _labels    # [FIX-B2] declare local to prevent global namespace leak
  read -ra _labels <<< "$HOSTNAME_VAL"
  for label in "${_labels[@]}"; do
    if [[ ! "$label" =~ $label_re ]]; then
      log_error "Invalid hostname label '${label}' in '${HOSTNAME_VAL}'."
      exit "$EXIT_VALIDATION"
    fi
  done
}

# [FIX-S2] Validate username: POSIX portable filename + Linux useradd constraints:
#           starts with letter or underscore, followed by letters/digits/hyphens/underscores,
#           no spaces, no shell metacharacters, max 32 chars.
validate_username() {
  if [[ -z "$USERNAME" ]]; then return 0; fi  # emptiness checked in validate_required_args
  if [[ ${#USERNAME} -gt 32 ]]; then
    log_error "Username '${USERNAME}' exceeds 32 characters."
    exit "$EXIT_VALIDATION"
  fi
  if [[ ! "$USERNAME" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
    log_error "Invalid username '${USERNAME}'. Use only lowercase letters, digits, hyphens, underscores; must start with letter or underscore."
    exit "$EXIT_VALIDATION"
  fi
}

# [FIX-S3] Validate LV size arguments accept only numeric + G|M|T|GiB|MiB|TiB suffix.
#           Also ensures validate_disk_size arithmetic stays correct (strips suffix safely).
validate_lv_sizes() {
  local size_re='^[1-9][0-9]*(G|M|T|GiB|MiB|TiB)$'
  if [[ ! "$LV_ROOT_SIZE" =~ $size_re ]]; then
    log_error "Invalid --lv-root-size '${LV_ROOT_SIZE}'. Use numeric value with G/M/T/GiB/MiB/TiB (e.g. 50G)."
    exit "$EXIT_VALIDATION"
  fi
  if [[ ! "$LV_SWAP_SIZE" =~ $size_re ]]; then
    log_error "Invalid --lv-swap-size '${LV_SWAP_SIZE}'. Use numeric value with G/M/T/GiB/MiB/TiB (e.g. 8G)."
    exit "$EXIT_VALIDATION"
  fi
}

# [FIX-B4] Validate --ids-home-net: allow only CIDR/IP characters to prevent YAML injection.
#           Accepts bare CIDRs (10.0.0.0/8), Snort list ([10.0.0.0/8,192.168.0.0/16]),
#           or quoted strings. Rejects shell-special and YAML-special chars.
validate_ids_home_net() {
  if [[ -z "$IDS_HOME_NET" ]]; then return 0; fi
  if [[ ! "$IDS_HOME_NET" =~ ^[\[\]0-9./:,\ a-fA-F!]+$ ]]; then
    log_error "Invalid --ids-home-net '${IDS_HOME_NET}'. Use CIDR notation only (e.g. [192.168.0.0/16,10.0.0.0/8])."
    exit "$EXIT_VALIDATION"
  fi
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

# [F8] Validate disk has enough space for chosen LV sizes
validate_disk_size() {
  local disk_bytes
  disk_bytes="$(blockdev --getsize64 "$DISK" 2>/dev/null)" || {
    log_warn "Could not determine disk size for validation. Proceeding anyway."
    return 0
  }
  local disk_gib  # [FIX-B5] SC2155: declare separate from assignment
  disk_gib=$(( disk_bytes / 1073741824 ))

  # Parse sizes (G, GiB → GiB; M, MiB → MiB; T, TiB → TiB — normalise to GiB for comparison)
  local root_g swap_g min_g
  # Strip suffix variants to get numeric value in the given unit, then convert to GiB
  _to_gib() {
    local raw="$1"
    local num="${raw//[A-Za-z]/}"
    case "$raw" in
      *GiB|*G) echo "$num" ;;
      *MiB|*M) echo $(( num / 1024 )) ;;
      *TiB|*T) echo $(( num * 1024 )) ;;
      *) echo 0 ;;
    esac
  }
  root_g="$(_to_gib "$LV_ROOT_SIZE")"
  swap_g="$(_to_gib "$LV_SWAP_SIZE")"
  # +1G EFI + 2G overhead
  min_g=$(( root_g + swap_g + 3 ))

  log_info "Disk: ${disk_gib} GiB | Required: ≥${min_g} GiB (root=${root_g}G swap=${swap_g}G + EFI+overhead)"
  if (( disk_gib < min_g )); then
    log_error "Disk too small: ${disk_gib} GiB < required ${min_g} GiB."
    log_error "Reduce --lv-root-size or --lv-swap-size, or choose a larger disk."
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
  log_info "Partitions: EFI=${EFI_PART} | LUKS=${LUKS_PART}"
}

confirm_destructive() {
  if [[ "$YES_MODE" == "true" || "$GLOBAL_DRY_RUN" == "true" ]]; then
    return 0
  fi
  log_warn "⚠  About to ERASE ALL DATA on ${DISK}."
  printf '%b' "${_RED}${_BOLD}Type 'ERASE' to continue: ${_RST}"
  local answer
  read -r answer
  if [[ "$answer" != "ERASE" ]]; then
    log_error "Not confirmed. Aborting."
    exit "$EXIT_PRECONDITION"
  fi
}

prompt_luks_passphrase() {
  local p1 p2
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] Skipping LUKS passphrase prompt."
    return 0
  fi
  read -r -s -p $'\nEnter new LUKS passphrase: ' p1; printf '\n'
  read -r -s -p 'Confirm new LUKS passphrase: ' p2; printf '\n'
  if [[ -z "$p1" || "$p1" != "$p2" ]]; then
    log_error "LUKS passphrase mismatch or empty."
    exit "$EXIT_VALIDATION"
  fi
  LUKS_PASSPHRASE="$p1"
  unset p1 p2
}

# [FIX-B1] Prompt for user account password (applied to root + USERNAME via chpasswd)
prompt_user_passphrase() {
  local p1 p2
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] Skipping user passphrase prompt."
    return 0
  fi
  # Already collected by TUI wizard (whiptail passwordbox) — skip re-prompting
  if [[ -n "${USER_PASSPHRASE:-}" ]]; then
    return 0
  fi
  read -r -s -p $'\nEnter password for root and '"${USERNAME}"': ' p1; printf '\n'
  read -r -s -p 'Confirm password: ' p2; printf '\n'
  if [[ -z "$p1" || "$p1" != "$p2" ]]; then
    log_error "User passphrase mismatch or empty."
    exit "$EXIT_VALIDATION"
  fi
  USER_PASSPHRASE="$p1"
  unset p1 p2
}

validate_required_args() {
  if [[ -z "$HOSTNAME_VAL" ]]; then
    log_error "Missing required --hostname argument."
    exit "$EXIT_USAGE"
  fi
  if [[ -z "$USERNAME" ]]; then
    log_error "Missing required --username argument."
    exit "$EXIT_USAGE"
  fi
  validate_hostname  # [FIX-S1]
  validate_username  # [FIX-S2]
}

require_target_root_ready() {
  if [[ ! -d "$MNT_ROOT" ]]; then
    log_error "Target root '$MNT_ROOT' does not exist."
    exit "$EXIT_PRECONDITION"
  fi
  if [[ ! -f "$MNT_ROOT/etc/os-release" ]]; then
    log_error "Target root '$MNT_ROOT' not bootstrapped. Run core-install first."
    exit "$EXIT_PRECONDITION"
  fi
}

# --- chroot_pacman_install ----------------------------------------------------
chroot_pacman_install() {
  local mode="full-upgrade"
  local -a packages=("$@")
  [[ "$SKIP_FULL_UPGRADE" == "true" ]] && mode="install-only"

  log_info "Pacman mode=${mode} packages=${packages[*]}"
  append_transaction_log "mode=${mode} packages=${packages[*]}"

  if [[ "$SKIP_FULL_UPGRADE" == "false" && "$PACMAN_UPGRADED_ONCE" == "false" ]]; then
    run_cmd arch-chroot "$MNT_ROOT" pacman -Syyu --noconfirm
    PACMAN_UPGRADED_ONCE="true"
  fi
  run_cmd arch-chroot "$MNT_ROOT" pacman -S --needed --noconfirm "${packages[@]}"
}

# --- Partition, Encrypt, LVM --------------------------------------------------
partition_disk() {
  log_step "Partitioning ${DISK} (GPT: EFI + LUKS)."
  run_cmd sgdisk --zap-all "$DISK"
  run_cmd sgdisk -n 1:1MiB:+512MiB -t 1:ef00 -c 1:"EFI" "$DISK"
  run_cmd sgdisk -n 2:0:0 -t 2:8309 -c 2:"CRYPTLVM" "$DISK"

  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    # Flush partition table to kernel; required after re-partitioning an in-use disk
    partprobe "$DISK" 2>/dev/null || true
    udevadm settle --timeout=5 2>/dev/null || true
    if [[ ! -b "$EFI_PART" || ! -b "$LUKS_PART" ]]; then
      log_error "Partition creation failed: expected ${EFI_PART} and ${LUKS_PART}."
      exit "$EXIT_RUNTIME"
    fi
    log_ok "Partitions created: ${EFI_PART} ${LUKS_PART}"
  fi
}

setup_encryption_lvm() {
  log_step "Creating LUKS2 container + LVM stack."
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    # [F9] Dry-run: use echo pipe so cryptsetup doesn't hang waiting for stdin
    log_info "[dry-run] cryptsetup luksFormat --type luks2 ${LUKS_PART}"
    log_info "[dry-run] cryptsetup open ${LUKS_PART} ${LUKS_NAME}"
  else
    if [[ -z "${LUKS_PASSPHRASE:-}" ]]; then
      log_error "Internal: missing LUKS passphrase."
      exit "$EXIT_RUNTIME"
    fi
    printf '%s' "$LUKS_PASSPHRASE" | cryptsetup luksFormat --type luks2 "$LUKS_PART" -
    printf '%s' "$LUKS_PASSPHRASE" | cryptsetup open "$LUKS_PART" "$LUKS_NAME" -
    unset LUKS_PASSPHRASE
    log_ok "LUKS2 container opened at /dev/mapper/${LUKS_NAME}"
  fi

  run_cmd pvcreate "/dev/mapper/${LUKS_NAME}"
  run_cmd vgcreate "$VG_NAME" "/dev/mapper/${LUKS_NAME}"
  run_cmd lvcreate -L "$LV_SWAP_SIZE" -n "$LV_SWAP" "$VG_NAME"
  run_cmd lvcreate -L "$LV_ROOT_SIZE" -n "$LV_ROOT" "$VG_NAME"
  run_cmd lvcreate -l 100%FREE -n "$LV_HOME" "$VG_NAME"
  log_ok "LVM: VG=${VG_NAME} LVs=${LV_ROOT}(${LV_ROOT_SIZE}) ${LV_SWAP}(${LV_SWAP_SIZE}) ${LV_HOME}(rest)"
}

format_and_mount() {
  log_step "Formatting and mounting filesystems."
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
      log_error "Mount validation failed: $MNT_ROOT/boot missing."
      exit "$EXIT_RUNTIME"
    fi
    log_ok "Filesystems mounted under ${MNT_ROOT}"
  fi
}

install_base() {
  log_step "Installing base packages with pacstrap."
  # [F5] iwd included when nm-iwd backend selected
  local -a base_pkgs=(
    base linux linux-firmware lvm2 cryptsetup grub efibootmgr
    networkmanager sudo vim git mkinitcpio
    ufw wireguard-tools openvpn
  )
  if [[ "$WIFI_BACKEND" == "nm-iwd" ]]; then
    base_pkgs+=(iwd)
    log_info "nm-iwd selected: adding iwd to pacstrap packages."
  fi

  # Pre-create vconsole.conf so pacstrap's mkinitcpio post-install hook (sd-vconsole) succeeds
  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    mkdir -p "$MNT_ROOT/etc"
    echo "KEYMAP=us" > "$MNT_ROOT/etc/vconsole.conf"
  fi
  run_cmd pacstrap "$MNT_ROOT" "${base_pkgs[@]}"
  append_transaction_log "pacstrap-packages=${base_pkgs[*]}"

  # [F6] genfstab: only write to fstab in real mode, not dry-run
  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    genfstab -U "$MNT_ROOT" >> "$MNT_ROOT/etc/fstab"
    log_ok "fstab generated."
  else
    log_info "[dry-run] would run: genfstab -U ${MNT_ROOT} >> ${MNT_ROOT}/etc/fstab"
  fi
}

# --- Chroot configuration script generator -----------------------------------
write_chroot_script() {
  # [F2] Script name updated to blk7arch_chroot.sh
  local chroot_script="$MNT_ROOT/root/blk7arch_chroot.sh"

  dedup_locales  # [F13] deduplicate before writing

  # Build comma-separated locale list
  local locale_csv=""
  local idx
  for idx in "${!LOCALES[@]}"; do
    [[ "$idx" -gt 0 ]] && locale_csv+=","
    locale_csv+="${LOCALES[$idx]}"
  done

  # [F12] iwd enable flag
  local enable_iwd="false"
  [[ "$WIFI_BACKEND" == "nm-iwd" ]] && enable_iwd="true"

  cat > "$chroot_script" <<CHROOT
#!/usr/bin/env bash
set -euo pipefail

HOSTNAME_VAL="${HOSTNAME_VAL}"
USERNAME="${USERNAME}"
TIMEZONE="${TIMEZONE}"
WIFI_BACKEND="${WIFI_BACKEND}"
ALLOW_SSH_INBOUND="${ALLOW_SSH_INBOUND}"
LUKS_PART="${LUKS_PART}"
LUKS_NAME="${LUKS_NAME}"
VG_NAME="${VG_NAME}"
LV_ROOT="${LV_ROOT}"
LOCALES_CSV="${locale_csv}"
ENABLE_IWD="${enable_iwd}"

# Timezone
ln -sf "/usr/share/zoneinfo/\${TIMEZONE}" /etc/localtime
hwclock --systohc

# Locales — [F4] use fixed-string grep to prevent regex injection
# [FIX-S8b] IFS=',' scoped to read via env-prefix; local not valid outside functions
IFS=',' read -r -a LOCALES <<< "\${LOCALES_CSV}"
for loc in "\${LOCALES[@]}"; do
  if ! grep -qF "\${loc} UTF-8" /etc/locale.gen; then
    echo "\${loc} UTF-8" >> /etc/locale.gen
  fi
  # Enable the locale (remove leading #) using fixed-string sed target
  sed -i "s|^#\\(\${loc} UTF-8\\)|\\1|" /etc/locale.gen
done
locale-gen
printf 'LANG=%s\n' "\${LOCALES[0]}" > /etc/locale.conf

# Hostname
echo "\${HOSTNAME_VAL}" > /etc/hostname
cat > /etc/hosts <<EOFH
127.0.0.1 localhost
::1       localhost
127.0.1.1 \${HOSTNAME_VAL}.localdomain \${HOSTNAME_VAL}
EOFH

# Console keymap (required by keymap + consolefont mkinitcpio hooks)
echo "KEYMAP=us" > /etc/vconsole.conf

# mkinitcpio with encrypt + lvm2 hooks
sed -i 's/^HOOKS=.*/HOOKS=(base udev autodetect modconf kms keyboard keymap consolefont block encrypt lvm2 filesystems fsck)/' /etc/mkinitcpio.conf
mkinitcpio -P

# GRUB with cryptdevice
luks_uuid="\$(blkid -s UUID -o value "\${LUKS_PART}")"
if [[ -z "\${luks_uuid}" ]]; then
  echo "[ERROR] Failed to determine LUKS UUID for \${LUKS_PART}" >&2
  exit 1
fi
sed -i "s|^GRUB_CMDLINE_LINUX=.*|GRUB_CMDLINE_LINUX=\\\"cryptdevice=UUID=\${luks_uuid}:\${LUKS_NAME} root=/dev/\${VG_NAME}/\${LV_ROOT}\\\"|" /etc/default/grub
# [F7] --efi-directory=/boot is correct when EFI is mounted at /boot
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB --recheck
grub-mkconfig -o /boot/grub/grub.cfg

# NetworkManager
systemctl enable NetworkManager
if [[ "\${WIFI_BACKEND}" == "nm-iwd" ]]; then
  mkdir -p /etc/NetworkManager/conf.d
  cat > /etc/NetworkManager/conf.d/wifi_backend.conf <<EOFW
[device]
wifi.backend=iwd
EOFW
fi
# [F12] Enable iwd when selected
if [[ "\${ENABLE_IWD}" == "true" ]]; then
  systemctl enable iwd
fi

# User creation
if ! id -u "\${USERNAME}" >/dev/null 2>&1; then
  useradd -m -G wheel -s /bin/bash "\${USERNAME}"
fi
echo '%wheel ALL=(ALL:ALL) ALL' > /etc/sudoers.d/10-wheel
chmod 0440 /etc/sudoers.d/10-wheel

# UFW firewall
ufw default deny incoming
ufw default allow outgoing
if [[ "\${ALLOW_SSH_INBOUND}" == "true" ]]; then
  ufw allow ssh
fi
ufw --force enable
systemctl enable ufw
CHROOT
  chmod 0700 "$chroot_script"
}

configure_chroot() {
  log_step "Configuring installed system in chroot."
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] would run blk7arch_chroot.sh in arch-chroot."
    return 0
  fi
  write_chroot_script
  arch-chroot "$MNT_ROOT" /bin/bash /root/blk7arch_chroot.sh
  rm -f "$MNT_ROOT/root/blk7arch_chroot.sh"
  log_ok "Chroot configuration complete."
}

# --- BlackArch ----------------------------------------------------------------
configure_blackarch() {
  if [[ "$ENABLE_BLACKARCH" != "true" ]]; then
    log_info "BlackArch disabled."
    return 0
  fi
  log_step "BlackArch bootstrap (verify=${BLACKARCH_VERIFY_MODE})."
  local strap="${MNT_ROOT}/root/strap.sh"
  local strap_sha_file="${MNT_ROOT}/root/strap.sh.sha256"
  run_cmd curl -fsSL --max-time 60 --retry 3 --retry-delay 5 -o "$strap" https://blackarch.org/strap.sh
  if [[ "$BLACKARCH_VERIFY_MODE" == "remote-sha256" ]]; then
    run_cmd curl -fsSL --max-time 30 --retry 3 --retry-delay 5 -o "$strap_sha_file" https://blackarch.org/strap.sh.sha256
  fi

  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] Would verify BlackArch strap via ${BLACKARCH_VERIFY_MODE}."
    return 0
  fi

  if [[ ! -f "$strap" ]]; then
    log_error "BlackArch strap download failed."
    exit "$EXIT_RUNTIME"
  fi

  if [[ "$BLACKARCH_VERIFY_MODE" == "remote-sha256" ]]; then
    if [[ ! -f "$strap_sha_file" ]]; then
      log_error "BlackArch checksum download failed."
      exit "$EXIT_RUNTIME"
    fi
    local expected_sha actual_sha
    expected_sha="$(awk '{print $1}' "$strap_sha_file")"
    actual_sha="$(sha256sum "$strap" | awk '{print $1}')"
    if [[ -z "$expected_sha" ]]; then
      log_error "Empty SHA256 from checksum file."
      exit "$EXIT_RUNTIME"
    fi
    if [[ "$actual_sha" != "$expected_sha" ]]; then
      log_error "BlackArch integrity failure: got ${actual_sha}, expected ${expected_sha}."
      exit "$EXIT_RUNTIME"
    fi
    # [FIX-L2] Both strap.sh and its .sha256 come from the same server — a compromised
    #           server could serve a matching fake pair and pass this check.
    #           For stronger assurance, verify the strap.sh GPG signature manually
    #           before running this installer with --enable-blackarch true.
    log_ok "BlackArch strap SHA256 verified."
    log_warn "NOTE (L2): strap.sh and .sha256 share the same origin server. A server-side"
    log_warn "compromise could forge a matching pair. For critical installs, verify GPG manually."
  elif [[ "$BLACKARCH_VERIFY_MODE" == "disabled" ]]; then
    log_warn "BlackArch checksum verification DISABLED — strap.sh authenticity unverified."
  fi

  chmod 0700 "$strap"  # [FIX-S7] explicit 0700: only root can read/execute
  arch-chroot "$MNT_ROOT" /bin/bash /root/strap.sh
  log_ok "BlackArch bootstrap complete."
}

# --- yum compat ---------------------------------------------------------------
install_yum_compat() {
  [[ "$INSTALL_YUM_COMPAT" != "true" ]] && return 0
  log_step "Installing yum compatibility (dnf + symlink)."
  chroot_pacman_install dnf
  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    run_cmd arch-chroot "$MNT_ROOT" ln -sf /usr/bin/dnf /usr/bin/yum
    append_transaction_log "installed-yum-compat=true"
    log_ok "yum → dnf symlink installed."
  else
    log_info "[dry-run] would symlink /usr/bin/yum → /usr/bin/dnf"
  fi
}

# --- Post-boot validation service --------------------------------------------
setup_postboot_validation() {
  [[ "$TEST_REPORT" != "true" ]] && return 0
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "[dry-run] would install post-boot validation service."
    return 0
  fi
  log_step "Installing post-boot validation service."
  mkdir -p "$MNT_ROOT/usr/local/sbin" "$MNT_ROOT/etc/systemd/system"
  cat > "$MNT_ROOT/usr/local/sbin/blk7arch-postboot-validate.sh" <<'EOF_PBV'
#!/usr/bin/env bash
set -euo pipefail
LOG_FILE="/var/log/blk7arch-postboot-check.log"
OK_FILE="/var/log/blk7arch-postboot-check.ok"
{
  echo "postboot_check_started=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  grep -q "cryptdevice=" /proc/cmdline && echo "cryptdevice_cmdline=ok" || echo "cryptdevice_cmdline=missing"
  systemctl is-enabled NetworkManager >/dev/null 2>&1 && echo "networkmanager_enabled=ok" || echo "networkmanager_enabled=missing"
  test -f /etc/fstab && echo "fstab_present=ok" || echo "fstab_present=missing"
  echo "postboot_check_finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "$LOG_FILE"
touch "$OK_FILE"
EOF_PBV
  chmod 0700 "$MNT_ROOT/usr/local/sbin/blk7arch-postboot-validate.sh"  # [FIX-B3] explicit perms, consistent with FIX-S7

  cat > "$MNT_ROOT/etc/systemd/system/blk7arch-postboot-validate.service" <<'EOF_SVC'
[Unit]
Description=BLK7ARCH post-boot validation
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/blk7arch-postboot-validate.sh

[Install]
WantedBy=multi-user.target
EOF_SVC
  run_cmd arch-chroot "$MNT_ROOT" systemctl enable blk7arch-postboot-validate.service
  write_test_report "stage=core-install reboot_validation=required"
  log_ok "Post-boot validation service installed."
}

# --- Workstation profile ------------------------------------------------------
install_workstation_profile() {
  log_step "Installing workstation profile (Hyprland stack)."
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
    if ! arch-chroot "$MNT_ROOT" id -u "$USERNAME" >/dev/null 2>&1; then
      log_warn "User '$USERNAME' missing — creating automatically."
      arch-chroot "$MNT_ROOT" useradd -m -G wheel -s /bin/bash "$USERNAME"
      append_transaction_log "auto-created-user=${USERNAME}"
      if [[ ! -d "$MNT_ROOT/home/$USERNAME" ]]; then
        mkdir -p "$MNT_ROOT/home/$USERNAME"
        arch-chroot "$MNT_ROOT" chown -R "$USERNAME:$USERNAME" "/home/$USERNAME"
        arch-chroot "$MNT_ROOT" chmod 0700 "/home/$USERNAME"
      fi
    fi
    if [[ ! -d "$MNT_ROOT/home/$USERNAME" ]]; then
      log_error "User home '$MNT_ROOT/home/$USERNAME' missing."
      exit "$EXIT_RUNTIME"
    fi
    mkdir -p "$target_dir"
    cat > "$target_dir/hyprland.conf" <<'EOFH'
# Minimal known-good Hyprland config written by BLK7ARCHv1.0 installer
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
    if arch-chroot "$MNT_ROOT" test -d "/home/$USERNAME/.config"; then
      arch-chroot "$MNT_ROOT" chown -R "$USERNAME:$USERNAME" "/home/$USERNAME/.config"
    fi
    log_ok "Hyprland config written to /home/$USERNAME/.config/hypr/hyprland.conf"
  else
    log_info "[dry-run] would create /home/$USERNAME/.config/hypr/hyprland.conf"
  fi
  write_test_report "stage=workstation-profile status=completed"
}

# --- IDS profile --------------------------------------------------------------
install_ids_profile() {
  log_step "Installing IDS profile (Snort + Suricata)."
  require_target_root_ready
  # [F3] ids-profile now validates required args
  validate_required_args

  # Check package availability
  local missing_packages=()
  for pkg in snort suricata; do
    if ! arch-chroot "$MNT_ROOT" pacman -Si "$pkg" >/dev/null 2>&1; then
      missing_packages+=("$pkg")
    fi
  done

  if [[ ${#missing_packages[@]} -gt 0 ]]; then
    log_warn "Not in standard repos: ${missing_packages[*]}"
    log_warn "Options: build from AUR (yay -S snort suricata) or use zeek/airodump-ng."
    write_test_report "stage=ids-profile status=skipped reason=packages-not-in-repos packages=${missing_packages[*]}"
    return 0
  fi

  chroot_pacman_install snort suricata

  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    local snort_dir="$MNT_ROOT/etc/snort"
    local suricata_dir="$MNT_ROOT/etc/suricata"
    local snort_profile_log="$MNT_ROOT/var/log/snort/profile-selection.log"
    local suricata_profile_log="$MNT_ROOT/var/log/suricata/profile-selection.log"

    mkdir -p "$snort_dir/rules" "$suricata_dir/rules"
    install -d -m 0750 "$MNT_ROOT/var/log/snort" "$MNT_ROOT/var/log/suricata"

    # Snort threshold
    cat > "$snort_dir/threshold.conf" <<'EOF_SNORTTH'
# Snort threshold — reduce noisy repeats
event_filter gen_id 1, sig_id 1000001, type limit, track by_src, count 1, seconds 60
event_filter gen_id 1, sig_id 1000002, type limit, track by_src, count 1, seconds 30
EOF_SNORTTH

    # Snort suppress
    if [[ -n "$IDS_SUPPRESS_FILE" ]]; then
      if [[ ! -f "$IDS_SUPPRESS_FILE" ]]; then
        log_error "Provided --ids-suppress-file '$IDS_SUPPRESS_FILE' not found."
        exit "$EXIT_VALIDATION"
      fi
      cp "$IDS_SUPPRESS_FILE" "$snort_dir/suppress.conf"
    else
      cat > "$snort_dir/suppress.conf" <<'EOF_SNORTSUP'
# Default suppressions — keep minimal to avoid hiding true positives.
# suppress gen_id 1, sig_id 2000001, track by_src, ip 10.0.0.0/8
EOF_SNORTSUP
    fi

    # Snort config
    cat > "$snort_dir/snort.conf" <<EOF_SNORT
# Precision-focused Snort profile generated by ${SCRIPT_NAME} v${VERSION}
var HOME_NET ${IDS_HOME_NET}
var EXTERNAL_NET !\$HOME_NET
config policy_mode: tap
config alert_with_interface_name
output alert_fast: /var/log/snort/alert.fast
include /etc/snort/threshold.conf
include /etc/snort/suppress.conf
include /etc/snort/rules/local.rules
EOF_SNORT

    # Snort rules
    cat > "$snort_dir/rules/local.rules" <<'EOF_SNORTRULES'
alert tcp any any -> $HOME_NET 22 (msg:"SNORT SSH brute-force"; flow:to_server,established; detection_filter:track by_src, count 12, seconds 60; sid:1000001; rev:1;)
alert icmp any any -> $HOME_NET any (msg:"SNORT ICMP flood"; itype:8; detection_filter:track by_src, count 80, seconds 10; sid:1000002; rev:1;)
EOF_SNORTRULES

    if [[ "$IDS_SNORT_PROFILE" == "strict" ]]; then
      cat >> "$snort_dir/rules/local.rules" <<'EOF_SNORTSTRICT'
alert tcp any any -> $HOME_NET 3389 (msg:"SNORT RDP brute-force"; flow:to_server,established; detection_filter:track by_src, count 10, seconds 60; sid:1000003; rev:1;)
EOF_SNORTSTRICT
    fi

    # Suricata config
    cat > "$suricata_dir/suricata.yaml" <<EOF_SURICATA
%YAML 1.1
---
vars:
  address-groups:
    HOME_NET: "${IDS_HOME_NET}"
    EXTERNAL_NET: "!\$HOME_NET"
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

    # Suricata rules
    cat > "$suricata_dir/rules/local.rules" <<'EOF_SURIRULES'
alert ssh any any -> $HOME_NET any (msg:"SURICATA SSH brute force"; flow:to_server,established; threshold:type both, track by_src, count 12, seconds 60; sid:2100001; rev:1;)
alert icmp any any -> $HOME_NET any (msg:"SURICATA ICMP flood"; itype:8; threshold:type both, track by_src, count 80, seconds 10; sid:2100002; rev:1;)
EOF_SURIRULES

    # Suricata threshold
    cat > "$suricata_dir/threshold.config" <<'EOF_SURITH'
threshold gen_id 1, sig_id 2100001, type both, track by_src, count 1, seconds 60
threshold gen_id 1, sig_id 2100002, type both, track by_src, count 1, seconds 30
EOF_SURITH

    # Managed rules mode
    if [[ "$IDS_MODE" == "managed-rules" ]]; then
      if ! arch-chroot "$MNT_ROOT" command -v suricata-update >/dev/null 2>&1; then
        log_warn "suricata-update missing — installing python-suricata-update."
        chroot_pacman_install python-suricata-update
      fi
      if ! arch-chroot "$MNT_ROOT" command -v suricata-update >/dev/null 2>&1; then
        log_error "managed-rules requires suricata-update. Use --ids-mode minimal-local or install manually."
        exit "$EXIT_RUNTIME"
      fi
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
      { echo "run_id=${RUN_ID}"; echo "ids_mode=${IDS_MODE}"; } > "$suricata_profile_log"
    else
      { echo "run_id=${RUN_ID}"; echo "ids_mode=${IDS_MODE}"; echo "local_rules_only=true"; } > "$suricata_profile_log"
    fi

    # Config tests
    run_cmd arch-chroot "$MNT_ROOT" snort -T -c /etc/snort/snort.conf
    run_cmd arch-chroot "$MNT_ROOT" suricata -T -c /etc/suricata/suricata.yaml -v
    { echo "run_id=${RUN_ID}"; echo "snort_profile=${IDS_SNORT_PROFILE}"; } > "$snort_profile_log"
    append_transaction_log "ids-mode=${IDS_MODE} snort-profile=${IDS_SNORT_PROFILE}"

    if [[ "$IDS_ENABLE_SERVICES" == "true" ]]; then
      run_cmd arch-chroot "$MNT_ROOT" systemctl enable snort.service suricata.service
      log_ok "snort.service + suricata.service enabled."
    fi
  else
    log_info "[dry-run] would install precision-tuned Snort + Suricata configs."
  fi
  write_test_report "stage=ids-profile status=completed ids_mode=${IDS_MODE}"
}

# --- Validation ---------------------------------------------------------------
run_validation() {
  log_step "Validating installation in ${MNT_ROOT}."
  require_target_root_ready
  local ok=true

  _check() {
    local desc="$1" cond="$2"
    if [[ "$cond" == "true" ]]; then
      log_ok "$desc"
    else
      log_error "FAIL: $desc"
      ok=false
    fi
  }

  [[ -f "$MNT_ROOT/etc/fstab" ]] && _f=true || _f=false
  _check "fstab exists" "$_f"

  [[ -f "$MNT_ROOT/etc/default/grub" ]] && _g=true || _g=false
  _check "grub defaults exist" "$_g"

  if [[ -f "$MNT_ROOT/etc/default/grub" ]]; then
    awk '/^GRUB_CMDLINE_LINUX=/{found=1} END{exit(found?0:1)}' "$MNT_ROOT/etc/default/grub" \
      && _gc=true || _gc=false
    _check "GRUB_CMDLINE_LINUX set" "$_gc"
  fi

  if [[ "$WIFI_BACKEND" == "nm-iwd" ]]; then
    [[ -f "$MNT_ROOT/etc/NetworkManager/conf.d/wifi_backend.conf" ]] && _nm=true || _nm=false
    _check "nm-iwd wifi_backend.conf exists" "$_nm"
  fi

  if [[ -d "$MNT_ROOT/home/$USERNAME/.config/hypr" ]]; then
    [[ -f "$MNT_ROOT/home/$USERNAME/.config/hypr/hyprland.conf" ]] && _hy=true || _hy=false
    _check "hyprland.conf exists" "$_hy"
  fi

  if [[ -f "$MNT_ROOT/etc/snort/snort.conf" ]]; then
    awk '/include \/etc\/snort\/rules\/local.rules/{found=1} END{exit(found?0:1)}' \
      "$MNT_ROOT/etc/snort/snort.conf" && _sr=true || _sr=false
    _check "snort.conf includes local.rules" "$_sr"
    awk '/include \/etc\/snort\/threshold.conf/{t=1} /include \/etc\/snort\/suppress.conf/{s=1} END{exit(t&&s?0:1)}' \
      "$MNT_ROOT/etc/snort/snort.conf" && _st=true || _st=false
    _check "snort.conf includes threshold+suppress" "$_st"
  fi

  if [[ -f "$MNT_ROOT/etc/suricata/suricata.yaml" ]]; then
    awk '/rule-files:/{rf=1} /- local.rules/{lr=1} END{exit(rf&&lr?0:1)}' \
      "$MNT_ROOT/etc/suricata/suricata.yaml" && _su=true || _su=false
    _check "suricata.yaml includes local.rules" "$_su"
    awk '/threshold-file:/{tf=1} END{exit(tf?0:1)}' \
      "$MNT_ROOT/etc/suricata/suricata.yaml" && _sth=true || _sth=false
    _check "suricata.yaml has threshold-file" "$_sth"
  fi

  [[ -f "$MNT_ROOT/var/log/blk7arch-install.log" ]] && _log=true || _log=false
  _check "transaction log exists" "$_log"

  if [[ "$TEST_REPORT" == "true" ]]; then
    [[ -f "$MNT_ROOT/var/log/blk7arch-test-report.txt" ]] && _tr=true || _tr=false
    _check "test report exists" "$_tr"
    if [[ -f "$MNT_ROOT/var/log/blk7arch-postboot-check.ok" ]]; then
      log_ok "Post-boot validation marker found."
    else
      log_warn "Post-boot marker missing — reboot target and check /var/log/blk7arch-postboot-check.log"
    fi
  fi

  if [[ "$ok" == "false" ]]; then
    log_error "Validation FAILED. See errors above."
    exit "$EXIT_VALIDATION"
  fi
  log_ok "Validation PASSED."
}

# --- core_install orchestrator -----------------------------------------------
core_install() {
  validate_required_args
  validate_timezone
  validate_locales
  validate_lv_sizes
  dedup_locales

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
    validate_disk_size
    resolve_partition_paths
    confirm_destructive
    prompt_luks_passphrase
    prompt_user_passphrase
  fi

  partition_disk
  setup_encryption_lvm
  format_and_mount
  install_base
  configure_chroot

  if [[ "$GLOBAL_DRY_RUN" == "false" ]]; then
    if [[ -z "${USER_PASSPHRASE:-}" ]]; then
      log_error "Internal: missing user passphrase."
      exit "$EXIT_RUNTIME"
    fi
    printf '%s:%s\n' "root" "$USER_PASSPHRASE" | arch-chroot "$MNT_ROOT" chpasswd
    printf '%s:%s\n' "$USERNAME" "$USER_PASSPHRASE" | arch-chroot "$MNT_ROOT" chpasswd
    unset USER_PASSPHRASE
    log_ok "Passwords set for root and ${USERNAME}."
  else
    log_info "[dry-run] would set passwords for root and ${USERNAME} via chpasswd."
  fi

  install_yum_compat
  setup_postboot_validation
  configure_blackarch
  write_test_report "stage=core-install status=completed"
  log_ok "Core installation completed successfully. run_id=${RUN_ID}"
}

# =============================================================================
# Unified UX: install wizard + config profiles
# =============================================================================

declare -A CFG=()
COMMAND_MODE=""
ADVANCED_MODE="false"
UNATTENDED_MODE="false"
CONFIG_FILE=""
CLI_DISK_EXPLICIT="false"
DISK_SOURCE="unset"
LEGACY_PROFILES=()

init_cfg_defaults() {
  CFG[profile]="workstation"
  CFG[workstation_mode]="base"
  CFG[disk]=""
  CFG[hostname]="blk7arch"
  CFG[username]="user"
  CFG[timezone]="${TIMEZONE}"
  CFG[locale]="${LOCALES[0]}"
  CFG[wifi_backend]="nm"
  CFG[root_size]=""
  CFG[swap_size]=""
  CFG[enable_blackarch]="false"
  CFG[allow_ssh_inbound]="false"
  CFG[ids_enabled]="false"
  CFG[yum_compat]="false"
  CFG[test_report]="false"
}

choose_from_menu() {
  local prompt="$1" default="$2"; shift 2
  local -a options=("$@")
  local idx=1 choice
  while true; do
    echo "$prompt"
    for choice in "${options[@]}"; do
      printf '  %d) %s\n' "$idx" "$choice"
      idx=$((idx+1))
    done
    idx=1
    read -r -p "Select [${default}]: " choice
    [[ -z "$choice" ]] && choice="$default"
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >=1 && choice <= ${#options[@]} )); then
      printf '%s' "${options[$((choice-1))]}"
      return 0
    fi
    echo "Invalid selection."
  done
}

calc_swap_default() {
  local mem_kb=0 mem_gb
  mem_kb="$(awk '/MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
  mem_gb=$(( (mem_kb + 1048575) / 1048576 ))
  if (( mem_gb <= 0 )); then echo "8G"; return; fi
  if (( mem_gb <= 4 )); then echo "4G"; elif (( mem_gb <= 8 )); then echo "8G"; elif (( mem_gb <= 16 )); then echo "16G"; else echo "32G"; fi
}

calc_root_default() {
  local disk_gib="$1" profile="$2"
  if (( disk_gib <= 80 )); then echo "40G"; return; fi
  case "$profile" in
    minimal) echo "35G" ;;
    core) echo "45G" ;;
    workstation) echo "60G" ;;
    pentest) echo "80G" ;;
    custom) echo "60G" ;;
    *) echo "50G" ;;
  esac
}

disk_is_placeholder() {
  local disk_value="${1:-}"
  case "$disk_value" in
    ""|changeme|CHANGEME|/dev/sdX|/dev/vdX|/dev/nvme0nX|/dev/nvmeXnY|/dev/*X|*'${'*|*'{{'*|*'>>'*|*'<<'*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

disk_is_valid_blockdev() {
  local disk_value="$1"
  [[ -b "$disk_value" ]]
}

detect_candidate_disks() {
  lsblk -dpno NAME,TYPE 2>/dev/null | awk '$2=="disk"{print $1}'
}

prompt_for_disk_manual() {
  local prompt_mode="${1:-menu}"
  local entry=""
  while true; do
    if [[ "$prompt_mode" == "empty-detection" ]]; then
      read -r -p "Enter target disk path (or 'retry'/'cancel'): " entry
      case "$entry" in
        retry|RETRY) return 2 ;;
        cancel|CANCEL)
          log_error "Disk selection cancelled by user."
          return 1
          ;;
      esac
    else
      read -r -p "Enter target disk path (or blank to return): " entry
      [[ -z "$entry" ]] && return 2
    fi

    if disk_is_placeholder "$entry"; then
      log_error "Invalid DISK value: template placeholder '${entry}' is not allowed."
      continue
    fi
    if ! disk_is_valid_blockdev "$entry"; then
      log_error "Invalid DISK value: '${entry}' is not a block device."
      continue
    fi

    CFG[disk]="$entry"
    DISK_SOURCE="interactive"
    return 0
  done
}

resolve_disk_interactive() {
  local disks=() dchoice entry
  while true; do
    list_disks_menu disks
    if (( ${#disks[@]} == 0 )); then
      log_warn "Disk auto-detection returned zero candidates."
      log_warn "No disks detected automatically. You can enter a disk path manually."
      prompt_for_disk_manual "empty-detection"
      case "$?" in
        0) return 0 ;;
        1)
          log_error "No disk selected. Choose a disk or enter one manually."
          return 1
          ;;
        2) continue ;;
      esac
    fi

    local -a labels=()
    for entry in "${disks[@]}"; do labels+=("$entry"); done
    echo "Detected disks:"
    local i=1
    for entry in "${labels[@]}"; do IFS='|' read -r d s m <<<"$entry"; echo "  $i) $d ($s $m)"; i=$((i+1)); done
    echo "  r) Refresh detection"
    echo "  m) Enter disk manually"
    echo "  c) Cancel"
    read -r -p "Select target disk [1]: " dchoice; dchoice="${dchoice:-1}"
    case "$dchoice" in
      r|R) continue ;;
      m|M)
        prompt_for_disk_manual "menu"
        case "$?" in
          0) return 0 ;;
          1) return 1 ;;
          2) continue ;;
        esac
        ;;
      c|C)
        log_error "Disk selection cancelled by user."
        log_error "No disk selected. Choose a disk or enter one manually."
        return 1
        ;;
      *)
        if [[ "$dchoice" =~ ^[0-9]+$ ]] && (( dchoice>=1 && dchoice<=${#labels[@]} )); then
          IFS='|' read -r CFG[disk] _ _ <<<"${labels[$((dchoice-1))]}"
          DISK_SOURCE="interactive"
          return 0
        fi
        echo "Invalid disk selection."
        ;;
    esac
  done
}

list_disks_menu() {
  local -n out_ref=$1
  out_ref=()
  while IFS= read -r dev; do
    local size model
    [[ -z "$dev" ]] && continue
    size="$(lsblk -dnpo SIZE "$dev" 2>/dev/null | head -n1)"
    model="$(lsblk -dnpo MODEL "$dev" 2>/dev/null | head -n1 | sed 's/^ *//;s/ *$//')"
    out_ref+=("${dev}|${size:-unknown}|${model:-unknown}")
  done < <(detect_candidate_disks)
}

apply_cfg_to_globals() {
  DISK="${CFG[disk]}"
  HOSTNAME_VAL="${CFG[hostname]}"
  USERNAME="${CFG[username]}"
  TIMEZONE="${CFG[timezone]}"
  LOCALES=("${CFG[locale]}")
  WIFI_BACKEND="${CFG[wifi_backend]}"
  LV_ROOT_SIZE="${CFG[root_size]}"
  LV_SWAP_SIZE="${CFG[swap_size]}"
  ENABLE_BLACKARCH="${CFG[enable_blackarch]}"
  ALLOW_SSH_INBOUND="${CFG[allow_ssh_inbound]}"
  TEST_REPORT="${CFG[test_report]}"
  INSTALL_YUM_COMPAT="${CFG[yum_compat]}"
}

load_config_file() {
  local cfg_file="$1"
  [[ -f "$cfg_file" ]] || { log_error "Config file not found: $cfg_file"; exit "$EXIT_USAGE"; }
  while IFS='=' read -r raw_k raw_v; do
    [[ -z "$raw_k" || "$raw_k" == \#* ]] && continue
    local k="${raw_k//[[:space:]]/}"
    local v="$raw_v"
    v="${v#\"}"
    v="${v%\"}"
    v="${v#'}"
    v="${v%'}"
    case "$k" in
      PROFILE) CFG[profile]="$v" ;;
      WORKSTATION_MODE) CFG[workstation_mode]="$v" ;;
      DISK) CFG[disk]="$v" ;;
      HOSTNAME) CFG[hostname]="$v" ;;
      USERNAME) CFG[username]="$v" ;;
      TIMEZONE) CFG[timezone]="$v" ;;
      LOCALE) CFG[locale]="$v" ;;
      WIFI_BACKEND) CFG[wifi_backend]="$v" ;;
      ROOT_LV_SIZE) CFG[root_size]="$v" ;;
      SWAP_LV_SIZE) CFG[swap_size]="$v" ;;
      ENABLE_BLACKARCH) CFG[enable_blackarch]="$(parse_bool "$v")" ;;
      ALLOW_SSH_INBOUND) CFG[allow_ssh_inbound]="$(parse_bool "$v")" ;;
      IDS_ENABLED) CFG[ids_enabled]="$(parse_bool "$v")" ;;
      YUM_COMPAT) CFG[yum_compat]="$(parse_bool "$v")" ;;
      TEST_REPORT) CFG[test_report]="$(parse_bool "$v")" ;;
      UNATTENDED) UNATTENDED_MODE="$(parse_bool "$v")" ;;
    esac
  done < "$cfg_file"
}

validate_install_cfg() {
  if [[ -z "${CFG[disk]}" ]]; then
    log_error "No disk selected. Choose a disk or enter one manually."
    exit "$EXIT_USAGE"
  fi
  if disk_is_placeholder "${CFG[disk]}"; then
    if [[ "$DISK_SOURCE" == "config" ]]; then
      log_error "Configured DISK is a template placeholder: ${CFG[disk]}"
    else
      log_error "Selected DISK is a template placeholder: ${CFG[disk]}"
    fi
    exit "$EXIT_VALIDATION"
  fi
  DISK="${CFG[disk]}"
  if [[ "$GLOBAL_DRY_RUN" != "true" ]]; then
    if ! disk_is_valid_blockdev "$DISK"; then
      if [[ "$DISK_SOURCE" == "config" ]]; then
        log_error "Configured DISK is not a block device: $DISK"
      else
        log_error "Selected DISK is not a block device: $DISK"
      fi
      exit "$EXIT_VALIDATION"
    fi
  fi
  HOSTNAME_VAL="${CFG[hostname]}"; USERNAME="${CFG[username]}"; validate_required_args
  TIMEZONE="${CFG[timezone]}"; validate_timezone
  LOCALES=("${CFG[locale]}"); validate_locales
  LV_ROOT_SIZE="${CFG[root_size]}"; LV_SWAP_SIZE="${CFG[swap_size]}"; validate_lv_sizes
  if [[ "${CFG[wifi_backend]}" != "nm" && "${CFG[wifi_backend]}" != "nm-iwd" ]]; then
    log_error "wifi_backend must be nm or nm-iwd"
    exit "$EXIT_VALIDATION"
  fi
}

print_install_summary() {
  echo
  echo "=== Installation Summary ==="
  printf 'Mode: %s\n' "$([[ "$ADVANCED_MODE" == "true" ]] && echo advanced || echo standard)"
  printf 'Profile: %s (%s)\n' "${CFG[profile]}" "${CFG[workstation_mode]}"
  printf 'Disk: %s\nHostname: %s\nUsername: %s\nTimezone: %s\nLocale: %s\n' \
    "${CFG[disk]}" "${CFG[hostname]}" "${CFG[username]}" "${CFG[timezone]}" "${CFG[locale]}"
  printf 'Root LV: %s | Swap LV: %s\nWiFi backend: %s\n' \
    "${CFG[root_size]}" "${CFG[swap_size]}" "${CFG[wifi_backend]}"
  printf 'BlackArch: %s | SSH inbound: %s | IDS: %s\n' \
    "${CFG[enable_blackarch]}" "${CFG[allow_ssh_inbound]}" "${CFG[ids_enabled]}"
}

confirm_execution() {
  if [[ "$GLOBAL_DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: skipping destructive confirmation barrier."
    YES_MODE="true"
    return 0
  fi
  local root_dev
  root_dev="$(findmnt -n -o SOURCE / || true)"
  if [[ -n "$root_dev" && "$root_dev" == ${CFG[disk]}* ]]; then
    log_error "Refusing to operate on current system disk: ${CFG[disk]}"
    exit "$EXIT_PRECONDITION"
  fi
  if lsblk -nr -o MOUNTPOINT "${CFG[disk]}" | grep -q '/'; then
    log_error "Refusing to install to a disk with mounted partitions: ${CFG[disk]}"
    exit "$EXIT_PRECONDITION"
  fi
  lsblk -dno NAME,SIZE,MODEL "${CFG[disk]}" | awk '{print "Target:","/dev/"$1,"Size:",$2,"Model:",$3}'
  echo "WARNING: ALL DATA ON ${CFG[disk]} WILL BE DESTROYED."
  if [[ "$UNATTENDED_MODE" == "true" ]]; then
    YES_MODE="true"
    return 0
  fi
  read -r -p "Type EXACTLY 'ERASE ${CFG[disk]}' to continue: " ans
  [[ "$ans" == "ERASE ${CFG[disk]}" ]] || { log_error "Confirmation phrase mismatch."; exit "$EXIT_PRECONDITION"; }
}

advanced_menu() {
  local choice
  while true; do
    choice="$(choose_from_menu 'Advanced options:' 1       'Set profile' 'Set workstation mode' 'Set timezone/locale' 'Set network/security' 'Set LV sizes' 'Continue')"
    case "$choice" in
      'Set profile') CFG[profile]="$(choose_from_menu 'Install profile:' 3 minimal core workstation pentest custom)" ;;
      'Set workstation mode') CFG[workstation_mode]="$(choose_from_menu 'Workstation mode:' 2 none base dev pentest custom)" ;;
      'Set timezone/locale')
        read -r -p "Timezone [${CFG[timezone]}]: " x; [[ -n "$x" ]] && CFG[timezone]="$x"
        read -r -p "Locale [${CFG[locale]}]: " x; [[ -n "$x" ]] && CFG[locale]="$x"
        ;;
      'Set network/security')
        CFG[wifi_backend]="$(choose_from_menu 'WiFi backend:' 1 nm nm-iwd)"
        CFG[allow_ssh_inbound]="$(choose_from_menu 'Allow inbound SSH?' 2 true false)"
        CFG[enable_blackarch]="$(choose_from_menu 'Enable BlackArch?' 2 true false)"
        CFG[ids_enabled]="$(choose_from_menu 'Enable IDS profile?' 2 true false)"
        ;;
      'Set LV sizes')
        read -r -p "Root LV size [${CFG[root_size]}]: " x; [[ -n "$x" ]] && CFG[root_size]="$x"
        read -r -p "Swap LV size [${CFG[swap_size]}]: " x; [[ -n "$x" ]] && CFG[swap_size]="$x"
        ;;
      'Continue') break ;;
    esac
  done
}

interactive_wizard() {
  local disk_gib entry
  if [[ -z "${CFG[disk]}" ]]; then
    if ! resolve_disk_interactive; then
      exit "$EXIT_VALIDATION"
    fi
  fi

  read -r -p "Hostname [${CFG[hostname]}]: " entry; [[ -n "$entry" ]] && CFG[hostname]="$entry"
  read -r -p "Username [${CFG[username]}]: " entry; [[ -n "$entry" ]] && CFG[username]="$entry"
  CFG[profile]="$(choose_from_menu 'Installation profile:' 3 minimal core workstation pentest custom)"
  CFG[workstation_mode]="$(choose_from_menu 'Workstation stack:' 2 none base dev pentest custom)"

  disk_gib="$(( $(blockdev --getsize64 "${CFG[disk]}" 2>/dev/null || echo 128849018880) / 1073741824 ))"
  [[ -z "${CFG[root_size]}" ]] && CFG[root_size]="$(calc_root_default "$disk_gib" "${CFG[profile]}")"
  [[ -z "${CFG[swap_size]}" ]] && CFG[swap_size]="$(calc_swap_default)"

  if [[ "$ADVANCED_MODE" == "true" ]]; then
    advanced_menu
  else
    read -r -p "Timezone [${CFG[timezone]}]: " entry; [[ -n "$entry" ]] && CFG[timezone]="$entry"
    read -r -p "Locale [${CFG[locale]}]: " entry; [[ -n "$entry" ]] && CFG[locale]="$entry"
  fi
}

run_workstation_modules() {
  case "${CFG[workstation_mode]}" in
    none) log_info "Skipping workstation modules." ;;
    base|dev|pentest|custom) install_workstation_profile ;;
  esac
  if [[ "${CFG[ids_enabled]}" == "true" || "${CFG[profile]}" == "pentest" || "${CFG[workstation_mode]}" == "pentest" ]]; then
    install_ids_profile
  fi
}

run_install() {
  apply_cfg_to_globals
  validate_install_cfg
  print_install_summary
  confirm_execution
  core_install
  run_workstation_modules
  if [[ "$GLOBAL_DRY_RUN" != "true" ]]; then
    run_validation
  else
    log_info "Dry-run mode: skipping post-install validation checks."
  fi
}

config_init() {
  local out="${1:-install.conf}"
  cat > "$out" <<'CFGEOF'
# BLK7ARCH install profile template
PROFILE=workstation
WORKSTATION_MODE=base
DISK=/dev/sdX
HOSTNAME=blk7arch
USERNAME=user
TIMEZONE=America/Sao_Paulo
LOCALE=en_US.UTF-8
WIFI_BACKEND=nm
ROOT_LV_SIZE=60G
SWAP_LV_SIZE=8G
ENABLE_BLACKARCH=false
ALLOW_SSH_INBOUND=false
IDS_ENABLED=false
YUM_COMPAT=false
TEST_REPORT=false
UNATTENDED=false
CFGEOF
  log_ok "Wrote config template: $out"
}

profile_list() {
  cat <<'EOF_P'
Available install profiles:
  minimal      Core encrypted base install without workstation modules
  core         Base encrypted install with conservative package set
  workstation  Opinionated desktop-ready install (default)
  pentest      Workstation + IDS + optional BlackArch-ready tuning
  custom       Start from defaults and customize in advanced menu
EOF_P
}

parse_install_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --advanced) ADVANCED_MODE="true"; shift ;;
      --config) CONFIG_FILE="${2:-}"; shift 2 ;;
      --unattended) UNATTENDED_MODE="true"; shift ;;
      --dry-run) GLOBAL_DRY_RUN="true"; shift ;;
      --yes) YES_MODE="true"; UNATTENDED_MODE="true"; shift ;;
      --hostname) CFG[hostname]="${2:-}"; shift 2 ;;
      --username) CFG[username]="${2:-}"; shift 2 ;;
      --disk) CFG[disk]="${2:-}"; CLI_DISK_EXPLICIT="true"; DISK_SOURCE="cli"; shift 2 ;;
      --timezone) CFG[timezone]="${2:-}"; shift 2 ;;
      --locale) CFG[locale]="${2:-}"; shift 2 ;;
      --lv-root-size) CFG[root_size]="${2:-}"; shift 2 ;;
      --lv-swap-size) CFG[swap_size]="${2:-}"; shift 2 ;;
      --wifi-backend) CFG[wifi_backend]="${2:-}"; shift 2 ;;
      --allow-ssh-inbound) CFG[allow_ssh_inbound]="$(parse_bool "${2:-}")"; shift 2 ;;
      --enable-blackarch) CFG[enable_blackarch]="$(parse_bool "${2:-}")"; shift 2 ;;
      *) log_error "Unknown install option: $1"; exit "$EXIT_USAGE" ;;
    esac
  done
}

parse_common_flags() {
  parse_install_args "$@"
}

usage() {
  cat <<USAGE
BLK7ARCHv${VERSION} — Unified Arch Linux encrypted installer

Usage:
  ${SCRIPT_NAME} install [--advanced] [--config FILE] [--unattended] [--dry-run]
  ${SCRIPT_NAME} config-init [output-file]
  ${SCRIPT_NAME} profile-list
  ${SCRIPT_NAME} self-test
  ${SCRIPT_NAME} help

Primary workflow:
  ${SCRIPT_NAME} install
  ${SCRIPT_NAME} install --advanced
  ${SCRIPT_NAME} install --config install.conf

Legacy compatibility (deprecated):
  core-install, workstation-profile, ids-profile, validate, dry-run
USAGE
}

main() {
  init_cfg_defaults
  local subcommand="${1:-help}"
  [[ $# -gt 0 ]] && shift

  case "$subcommand" in
    install)
      parse_install_args "$@"
      local cli_disk=""
      if [[ "$CLI_DISK_EXPLICIT" == "true" ]]; then
        cli_disk="${CFG[disk]}"
      fi
      if [[ -n "$CONFIG_FILE" ]]; then
        load_config_file "$CONFIG_FILE"
        if [[ "$CLI_DISK_EXPLICIT" == "true" ]]; then
          CFG[disk]="$cli_disk"
          DISK_SOURCE="cli"
        elif [[ -n "${CFG[disk]}" ]]; then
          DISK_SOURCE="config"
        fi
      fi
      if [[ -z "${CFG[disk]}" ]]; then
        interactive_wizard
      fi
      run_install
      log_ok "BLK7ARCHv${VERSION} installation complete!"
      ;;
    config-init)
      config_init "${1:-install.conf}"
      ;;
    profile-list)
      profile_list
      ;;
    self-test)
      GLOBAL_DRY_RUN="true"
      CFG[disk]="${CFG[disk]:-/dev/null}"
      CFG[hostname]="test-host"
      CFG[username]="tester"
      CFG[workstation_mode]="none"
      CFG[ids_enabled]="false"
      CFG[root_size]="50G"
      CFG[swap_size]="8G"
      run_install
      ;;
    core-install)
      log_warn "Deprecated: core-install. Use '${SCRIPT_NAME} install' instead."
      parse_install_args "$@"
      run_install
      ;;
    workstation-profile)
      log_warn "Deprecated: workstation-profile. Use '${SCRIPT_NAME} install' with workstation mode."
      parse_install_args "$@"
      apply_cfg_to_globals
      install_workstation_profile
      ;;
    ids-profile)
      log_warn "Deprecated: ids-profile. Use '${SCRIPT_NAME} install --advanced' and enable IDS."
      parse_install_args "$@"
      apply_cfg_to_globals
      install_ids_profile
      ;;
    validate)
      apply_cfg_to_globals
      run_validation
      ;;
    dry-run)
      log_warn "Deprecated: dry-run subcommand. Use install --dry-run."
      GLOBAL_DRY_RUN="true"
      parse_install_args "$@"
      if [[ -z "${CFG[disk]}" ]]; then CFG[disk]="/dev/null"; fi
      run_install
      ;;
    -h|--help|help|"")
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
