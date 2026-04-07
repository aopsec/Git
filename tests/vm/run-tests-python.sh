#!/usr/bin/env bash
# tests/vm/run-tests-python.sh — automated VM test for the blk7rch Python package
#
# Two modes:
#   --dry-only   Direct kernel boot (bypasses GRUB, no UEFI needed). Runs self-test
#                and install --dry-run only. Fast (~5 min). Safe — no disk writes.
#
#   (default)    UEFI boot via VNC display (OVMF + GRUB keyboard works).
#                Runs self-test, dry-run, and full install. (~50 min).
#
# Requires: qemu-system-x86_64, tmux, ncat (nmap-ncat), /dev/kvm
#           /tmp/arch-boot/{vmlinuz-linux,initramfs-linux.img}  ← for --dry-only
#           Extract with: 7z e archlinux-x86_64.iso arch/boot/x86_64/{vmlinuz-linux,initramfs-linux.img} -o/tmp/arch-boot
#
# Usage:
#   ./run-tests-python.sh               # full: UEFI boot + install (~50 min)
#   ./run-tests-python.sh --dry-only    # fast: direct kernel boot, no disk writes (~5 min)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ARTIFACTS="${SCRIPT_DIR}/artifacts"
LOGS="${SCRIPT_DIR}/logs"
DISK="${ARTIFACTS}/test-disk.qcow2"
OVMF_VARS="${ARTIFACTS}/OVMF_VARS.fd"
OVMF_CODE="/usr/share/edk2/ovmf/OVMF_CODE.fd"
ISO="/var/lib/libvirt/images/archlinux-x86_64.iso"
MON_SOCK="/tmp/blk7rch-python-qemu-mon.sock"
SESSION="blk7rch-python-test"
VNC_PORT=5930          # display :30 → port 5930 (unlikely to conflict)
KERNEL_DIR="/tmp/arch-boot"   # pre-extracted kernel + initrd (for --dry-only)

# Install parameters
LUKS_PASS="TestSecure1!"
HOSTNAME="blk7test"
USERNAME="auditor"
LV_ROOT="40G"
LV_SWAP="4G"
PROFILE="workstation"   # pentest omitted: snort/suricata not in standard repos

DRY_ONLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-only) DRY_ONLY=true ;;
    *) echo "[ERROR] Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

# ── helpers ──────────────────────────────────────────────────────────────────

log()  { printf '\e[1;34m[TEST] %s\e[0m\n' "$*" | tee -a "${LOGFILE:-/dev/stderr}"; }
ok()   { printf '\e[1;32m[ OK ] %s\e[0m\n' "$*" | tee -a "${LOGFILE:-/dev/stderr}"; }
fail() { printf '\e[1;31m[FAIL] %s\e[0m\n' "$*" | tee -a "${LOGFILE:-/dev/stderr}"; exit 1; }
warn() { printf '\e[1;33m[WARN] %s\e[0m\n' "$*" | tee -a "${LOGFILE:-/dev/stderr}"; }

pane_output() {
  tmux capture-pane -t "${SESSION}:0.0" -p -S - 2>/dev/null || true
}

wait_for() {
  local pattern="$1" timeout="${2:-120}" interval=3
  local elapsed=0
  while (( elapsed < timeout )); do
    if pane_output | grep -qE "$pattern"; then
      return 0
    fi
    sleep "$interval"
    (( elapsed += interval ))
  done
  warn "Timeout waiting for: $pattern"
  return 1
}

mon_cmd() {
  echo -e "${1}\n" | ncat -U "${MON_SOCK}" --recv-only 2>/dev/null || true
}

vm_enter() {
  tmux send-keys -t "${SESSION}:0.0" "$1" Enter
}

# ── preflight ────────────────────────────────────────────────────────────────

[[ -f "$DISK" && -f "$OVMF_VARS" ]] || fail "Artifacts missing — run ./setup.sh first"
[[ -f "$ISO"  ]] || fail "Arch ISO not found at $ISO"

if [[ "$DRY_ONLY" == "true" ]]; then
  [[ -f "${KERNEL_DIR}/vmlinuz-linux" && -f "${KERNEL_DIR}/initramfs-linux.img" ]] || \
    fail "Extracted kernel not found in ${KERNEL_DIR}. Run: 7z e ${ISO} arch/boot/x86_64/{vmlinuz-linux,initramfs-linux.img} -o${KERNEL_DIR}"
else
  [[ -f "$OVMF_CODE" ]] || {
    OVMF_CODE="/usr/share/OVMF/OVMF_CODE.fd"
    [[ -f "$OVMF_CODE" ]] || fail "OVMF firmware not found"
  }
fi

command -v ncat  &>/dev/null || fail "ncat not found (install nmap-ncat)"
command -v tmux  &>/dev/null || fail "tmux not found"
[[ -e /dev/kvm ]] || fail "/dev/kvm not available (enable KVM)"

mkdir -p "$LOGS"
LOGFILE="${LOGS}/python-test-$(date +%Y%m%d-%H%M%S).log"
log "Log file: ${LOGFILE}"
log "Mode: $( [[ "$DRY_ONLY" == "true" ]] && echo "dry-only (direct kernel boot)" || echo "full (UEFI + install)" )"

# ── launch VM ────────────────────────────────────────────────────────────────

tmux kill-session -t "${SESSION}" 2>/dev/null || true
rm -f "${MON_SOCK}"

if [[ "$DRY_ONLY" == "true" ]]; then
  # ── MODE A: Direct kernel boot — bypasses GRUB, no UEFI needed ───────────
  # Reliable for self-test + dry-run. No OVMF, no GRUB keyboard issue.

  log "Starting QEMU (direct kernel boot, serial→stdio)..."

  QEMU_CMD=(
    qemu-system-x86_64
    -enable-kvm
    -cpu host
    -m 4G
    -smp 4

    -kernel "${KERNEL_DIR}/vmlinuz-linux"
    -initrd "${KERNEL_DIR}/initramfs-linux.img"
    -append "archisobasedir=arch archisodevice=/dev/sr0 console=ttyS0,115200n8 quiet"

    -drive "file=${ISO},media=cdrom,readonly=on,if=ide"

    -netdev "user,id=net0,hostfwd=tcp::2223-:22"
    -device "virtio-net-pci,netdev=net0"

    -virtfs "local,path=${REPO_ROOT},mount_tag=blk7arch,security_model=mapped-xattr,id=blk7arch"

    -serial stdio
    -display none
    -name "blk7rch-python-test"
  )

  QEMU_QUOTED=$(printf '%q ' "${QEMU_CMD[@]}")
  tmux new-session -d -s "${SESSION}" -x 220 -y 50 \
    "exec ${QEMU_QUOTED} 2>&1 | tee -a '${LOGFILE}'"

  log "QEMU started (direct kernel boot). Waiting for Arch ISO (~90s)..."
  wait_for "archiso login:|root@archiso" 180 || {
    pane_output | tail -30 >> "${LOGFILE}"
    fail "Arch ISO did not reach login prompt (direct boot)"
  }

else
  # ── MODE B: Full UEFI boot via VNC display ───────────────────────────────
  # VNC initialises OVMF ConIn so sendkey reaches GRUB → EFI Shell navigation works.
  # Required for full install (UEFI partition layout + EFI GRUB bootloader).

  log "Starting QEMU (UEFI + VNC display on :${VNC_PORT})..."

  QEMU_CMD=(
    qemu-system-x86_64
    -enable-kvm
    -cpu host
    -m 4G
    -smp 4

    -drive "if=pflash,format=raw,readonly=on,file=${OVMF_CODE}"
    -drive "if=pflash,format=raw,file=${OVMF_VARS}"
    -drive "file=${DISK},if=virtio,format=qcow2,cache=writeback"
    -drive "file=${ISO},media=cdrom,readonly=on,if=ide"
    -boot "order=dc"

    -netdev "user,id=net0,hostfwd=tcp::2223-:22"
    -device "virtio-net-pci,netdev=net0"

    -virtfs "local,path=${REPO_ROOT},mount_tag=blk7arch,security_model=mapped-xattr,id=blk7arch"

    # USB keyboard: GRUB in UEFI mode uses EFI HID protocol, not PS/2.
    # Adding usb-kbd ensures sendkey events reach GRUB via OVMF's USB driver.
    -device usb-ehci,id=usb0
    -device usb-kbd,bus=usb0.0

    -serial stdio
    -monitor "unix:${MON_SOCK},server,nowait"
    -display "vnc=127.0.0.1:$((VNC_PORT - 5900))"   # VNC display index = port - 5900

    -name "blk7rch-python-test"
  )

  QEMU_QUOTED=$(printf '%q ' "${QEMU_CMD[@]}")
  tmux new-session -d -s "${SESSION}" -x 220 -y 50 \
    "exec ${QEMU_QUOTED} 2>&1 | tee -a '${LOGFILE}'"

  log "QEMU started. Waiting for monitor socket..."
  for i in $(seq 1 15); do [[ -S "${MON_SOCK}" ]] && break; sleep 1; done
  [[ -S "${MON_SOCK}" ]] || fail "QEMU monitor socket not created"

  # Navigate Arch ISO GRUB menu → EFI Shell
  # Menu (15s countdown, 0-indexed):
  #   0: Arch Linux install medium (UEFI)  ← default
  #   1: Arch Linux with speech
  #   2: Memtest86+
  #   3: EFI Shell                         ← target (Down×3 + Enter)
  log "Waiting for GRUB menu (~5s)..."
  wait_for "Boot in" 20 || warn "GRUB countdown not visible — sending keys anyway"

  # Stop countdown immediately: send a neutral key (shift), then navigate
  mon_cmd "sendkey shift"
  sleep 0.5

  log "Navigating to EFI Shell (Down×3 + Enter)..."
  for i in 1 2 3; do mon_cmd "sendkey down"; sleep 0.5; done
  mon_cmd "sendkey ret"

  log "Waiting for EFI Shell (~20s)..."
  if ! wait_for "Shell>" 45; then
    warn "EFI Shell not detected — retrying..."
    for i in 1 2 3; do mon_cmd "sendkey down"; sleep 0.5; done
    mon_cmd "sendkey ret"
    wait_for "Shell>" 30 || { pane_output | tail -30 >> "${LOGFILE}"; fail "Could not reach EFI Shell"; }
  fi
  ok "EFI Shell ready"

  # Boot Arch ISO kernel with serial console
  ARCH_BOOT="FS0:\\arch\\boot\\x86_64\\vmlinuz-linux"
  ARCH_INITRD="\\arch\\boot\\x86_64\\initramfs-linux.img"
  KCMD="${ARCH_BOOT} archisobasedir=arch archisodevice=/dev/sr0 initrd=${ARCH_INITRD} console=ttyS0,115200n8 quiet"
  log "Booting kernel with console=ttyS0..."
  vm_enter "$KCMD"

  log "Waiting for Arch ISO to boot (~120s)..."
  wait_for "archiso login:|root@archiso" 180 || {
    pane_output | tail -30 >> "${LOGFILE}"
    fail "Arch ISO did not reach login prompt (UEFI boot)"
  }
fi

ok "Arch ISO booted"
vm_enter "root"
sleep 3

# ── mount host 9p share ──────────────────────────────────────────────────────

log "Mounting host 9p share..."
vm_enter "mkdir -p /host && mount -t 9p -o trans=virtio,version=9p2000.L blk7arch /host"
sleep 3
vm_enter "ls /host/blk7rch/blk7rch/__init__.py && echo '9P_OK'"
wait_for "9P_OK" 15 || fail "9p share not accessible"
ok "9p share mounted"

# ── verify blk7rch importable ────────────────────────────────────────────────

log "Verifying blk7rch importable..."
vm_enter "PYTHONPATH=/host/blk7rch python -c 'import blk7rch; print(\"IMPORT_OK\")'"
wait_for "IMPORT_OK" 20 || fail "blk7rch not importable (archinstall missing?)"
ok "blk7rch importable"

# ── generate config file ─────────────────────────────────────────────────────

log "Generating install config..."
vm_enter "PYTHONPATH=/host/blk7rch python -m blk7rch config-init /tmp/test-config.json --profile ${PROFILE} && echo 'CONFIG_OK'"
wait_for "CONFIG_OK" 20 || fail "config-init failed"

# Patch disk, hostname, username into the config via Python
vm_enter "python -c \"
import json, sys
with open('/tmp/test-config.json') as f: c = json.load(f)
c['disk']     = '/dev/vda'
c['hostname'] = '${HOSTNAME}'
c['username'] = '${USERNAME}'
with open('/tmp/test-config.json', 'w') as f: json.dump(c, f, indent=2)
print('PATCH_OK')
\""
wait_for "PATCH_OK" 10 || fail "config patch failed"
ok "Config generated and patched"

# ── SELF-TEST ─────────────────────────────────────────────────────────────────

SELFTEST_RC=99
SELFTEST_MARKER="SELFTEST_$$"
log "=== self-test (dry-run pentest profile) ==="
vm_enter "PYTHONPATH=/host/blk7rch python -m blk7rch self-test && echo '${SELFTEST_MARKER}:0' || echo '${SELFTEST_MARKER}:1'"
if wait_for "${SELFTEST_MARKER}" 90; then
  pane_output | grep -qE "${SELFTEST_MARKER}:1" && SELFTEST_RC=1 || SELFTEST_RC=0
fi
(( SELFTEST_RC == 0 )) && ok "SELF-TEST: PASSED" || warn "SELF-TEST: FAILED (${SELFTEST_RC})"
echo "SELFTEST_RESULT=${SELFTEST_RC}" >> "${LOGFILE}"

# ── DRY-RUN TEST ─────────────────────────────────────────────────────────────

DRY_RC=99
DRYRUN_MARKER="DRYRUN_$$"
log "=== install --dry-run --profile ${PROFILE} ==="
vm_enter "PYTHONPATH=/host/blk7rch python -m blk7rch install \
  --dry-run --config /tmp/test-config.json --unattended \
  && echo '${DRYRUN_MARKER}:0' || echo '${DRYRUN_MARKER}:1'"
if wait_for "${DRYRUN_MARKER}" 180; then
  pane_output | grep -qE "${DRYRUN_MARKER}:1" && DRY_RC=1 || DRY_RC=0
fi
(( DRY_RC == 0 )) && ok "DRY-RUN: PASSED" || warn "DRY-RUN: FAILED (${DRY_RC})"
echo "DRY_RUN_RESULT=${DRY_RC}" >> "${LOGFILE}"

# ── FULL INSTALL (UEFI mode only) ─────────────────────────────────────────────

INSTALL_RC=skip
if [[ "$DRY_ONLY" == "false" ]]; then
  INSTALL_MARKER="INSTALL_$$"
  log "=== FULL INSTALL --profile ${PROFILE} (destructive — /dev/vda, ~40 min) ==="

  vm_enter "printf '{\"encryption_password\":\"%s\",\"user_password\":\"%s\",\"root_password\":\"%s\"}' \
    '${LUKS_PASS}' '${LUKS_PASS}' '${LUKS_PASS}' > /tmp/test-creds.json && chmod 600 /tmp/test-creds.json"
  sleep 2

  vm_enter "PYTHONPATH=/host/blk7rch python -m blk7rch install \
    --config /tmp/test-config.json \
    --creds /tmp/test-creds.json --unattended \
    && echo '${INSTALL_MARKER}:0' || echo '${INSTALL_MARKER}:1'"

  TIMEOUT=3000; ELAPSED=0; INSTALL_RC=99
  while (( ELAPSED < TIMEOUT )); do
    sleep 30; ELAPSED=$(( ELAPSED + 30 ))
    OUT=$(pane_output)
    echo "$OUT" | grep -qE "${INSTALL_MARKER}:0" && { INSTALL_RC=0; break; }
    echo "$OUT" | grep -qE "${INSTALL_MARKER}:1" && { INSTALL_RC=1; break; }
    (( ELAPSED % 120 == 0 )) && {
      LAST=$(echo "$OUT" | grep -iE "phase|step|pacstrap|mkinitcpio|grub|chroot|error" | tail -3)
      log "Progress (~${ELAPSED}s): ${LAST:-<waiting>}"
    }
  done
  pane_output >> "${LOGFILE}"
  (( INSTALL_RC == 0 )) && ok "FULL INSTALL: PASSED" || warn "FULL INSTALL: FAILED/timeout (${INSTALL_RC})"
  echo "INSTALL_RESULT=${INSTALL_RC}" >> "${LOGFILE}"
fi

# ── SUMMARY ──────────────────────────────────────────────────────────────────

log "=== TEST SUMMARY ==="
(( SELFTEST_RC == 0 )) && ok "self-test:    PASSED" || warn "self-test:    FAILED (${SELFTEST_RC})"
(( DRY_RC     == 0 )) && ok "dry-run:      PASSED" || warn "dry-run:      FAILED (${DRY_RC})"
[[ "$INSTALL_RC" == "skip" ]] || { (( INSTALL_RC == 0 )) && ok "full-install: PASSED" || warn "full-install: FAILED (${INSTALL_RC})"; }
log "Full log: ${LOGFILE}"
log "VM running in tmux '${SESSION}' — attach: tmux attach -t ${SESSION} | kill: tmux kill-session -t ${SESSION}"
