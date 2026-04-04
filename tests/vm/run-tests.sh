#!/usr/bin/env bash
# tests/vm/run-tests.sh — fully automated BLK7ARCHv1_0.sh test runner
#
# Launches QEMU headless, navigates OVMF → EFI Shell → kernel boot with
# console=ttyS0, then runs dry-run and core-install tests unattended.
#
# Requires: qemu-system-x86_64, ncat (for monitor socket), tmux
#
# Usage:
#   ./run-tests.sh              # dry-run + core-install
#   ./run-tests.sh --dry-only   # dry-run only (faster, ~3 min)
#   ./run-tests.sh --install-only
#
# Logs written to: tests/vm/logs/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ARTIFACTS="${SCRIPT_DIR}/artifacts"
LOGS="${SCRIPT_DIR}/logs"
DISK="${ARTIFACTS}/test-disk.qcow2"
OVMF_VARS="${ARTIFACTS}/OVMF_VARS.fd"
OVMF_CODE="/usr/share/edk2/ovmf/OVMF_CODE.fd"
ISO="/var/lib/libvirt/images/archlinux-x86_64.iso"
MON_SOCK="/tmp/blk7arch-qemu-mon.sock"
SESSION="vm-test"

# Arch ISO boot params (UUID from /boot/YYYY-MM-DD.uuid inside ISO)
ISO_UUID="2026-04-01-15-12-08-00"
KERNEL_CMD="FS0:\\arch\\boot\\x86_64\\vmlinuz-linux archisobasedir=arch archisosearchuuid=${ISO_UUID} initrd=\\arch\\boot\\x86_64\\initramfs-linux.img console=ttyS0,115200n8"

# Test credentials
LUKS_PASS="TestSecure1!"
HOSTNAME="archtest"
USERNAME="testuser"
LV_ROOT="40G"
LV_SWAP="4G"

RUN_DRY=true
RUN_INSTALL=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-only)      RUN_INSTALL=false ;;
    --install-only)  RUN_DRY=false ;;
    *) echo "[ERROR] Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

# ── helpers ──────────────────────────────────────────────────────────────────

log()  { printf '\e[1;34m[TEST] %s\e[0m\n' "$*"; }
ok()   { printf '\e[1;32m[ OK ] %s\e[0m\n' "$*"; }
fail() { printf '\e[1;31m[FAIL] %s\e[0m\n' "$*"; exit 1; }
warn() { printf '\e[1;33m[WARN] %s\e[0m\n' "$*"; }

pane_output() {
  tmux capture-pane -t "${SESSION}:0.0" -p -S - 2>/dev/null || true
}

# Wait for a pattern in the VM serial output; return 0 on match, 1 on timeout
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

# Send a command to the QEMU monitor socket
mon_cmd() {
  local cmd="$1"
  echo -e "${cmd}\n" | ncat -U "${MON_SOCK}" --recv-only 2>/dev/null || true
}

# Send keys to VM serial (via tmux pane stdin)
vm_send() {
  tmux send-keys -t "${SESSION}:0.0" "$1" ""
}
vm_enter() {
  tmux send-keys -t "${SESSION}:0.0" "$1" Enter
}

# ── preflight ────────────────────────────────────────────────────────────────

[[ -f "$DISK" && -f "$OVMF_VARS" ]] || fail "Artifacts missing — run ./setup.sh first"
[[ -f "$ISO" ]] || fail "Arch ISO not found at $ISO"
[[ -f "$OVMF_CODE" ]] || fail "OVMF firmware not found at $OVMF_CODE"
command -v ncat &>/dev/null || fail "ncat not found (install nmap-ncat)"
command -v tmux &>/dev/null || fail "tmux not found"

mkdir -p "$LOGS"
LOGFILE="${LOGS}/test-$(date +%Y%m%d-%H%M%S).log"
log "Log file: ${LOGFILE}"

# ── launch VM ────────────────────────────────────────────────────────────────

tmux kill-session -t "${SESSION}" 2>/dev/null || true
rm -f "${MON_SOCK}"

log "Starting QEMU (headless, serial→stdio, monitor→unix socket)..."

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

  -netdev "user,id=net0,hostfwd=tcp::2222-:22"
  -device "virtio-net-pci,netdev=net0"

  -virtfs "local,path=${REPO_ROOT},mount_tag=blk7arch,security_model=mapped-xattr,id=blk7arch"

  # Serial on stdio (captured by tmux pane)
  -serial stdio

  # QEMU monitor on unix socket (for OVMF sendkey navigation)
  -monitor "unix:${MON_SOCK},server,nowait"

  # No graphical display; all output via serial
  -display none

  -name "BLK7ARCH-test"
)

# Start QEMU inside a tmux session (so we can capture serial I/O)
tmux new-session -d -s "${SESSION}" -x 220 -y 50 \
  "exec ${QEMU_CMD[*]} 2>&1 | tee -a '${LOGFILE}'"

log "QEMU started in tmux session '${SESSION}'"
log "Waiting for OVMF to initialize (~5s)..."
sleep 6

# ── navigate OVMF boot manager → EFI Shell ───────────────────────────────────

log "Sending keystrokes to OVMF boot manager (Down×3 + Enter = EFI Shell)..."

# Wait for monitor socket to be ready
for i in $(seq 1 10); do
  [[ -S "${MON_SOCK}" ]] && break
  sleep 1
done
[[ -S "${MON_SOCK}" ]] || fail "QEMU monitor socket not created"

# Navigate: Down×3 selects EFI Shell, Enter confirms
# OVMF countdown is 15s; we send at ~6s — well within window
for i in 1 2 3; do
  mon_cmd "sendkey down"
  sleep 0.4
done
mon_cmd "sendkey ret"
log "OVMF navigation keys sent"

# ── wait for EFI Shell prompt ─────────────────────────────────────────────────

log "Waiting for EFI Shell prompt (~10s)..."
if ! wait_for "Shell>" 40; then
  warn "EFI Shell prompt not detected — dumping current output:"
  pane_output | tail -20
  # Try again: some OVMF builds require more key presses
  log "Retrying OVMF navigation..."
  for i in 1 2 3 4 5; do
    mon_cmd "sendkey down"
    sleep 0.3
  done
  mon_cmd "sendkey ret"
  if ! wait_for "Shell>" 30; then
    pane_output | tail -30 >> "${LOGFILE}"
    fail "Could not reach EFI Shell"
  fi
fi
ok "EFI Shell ready"

# ── boot Arch ISO kernel with serial console ──────────────────────────────────

log "Booting Arch ISO kernel with console=ttyS0..."
vm_enter "$KERNEL_CMD"

# ── wait for Arch ISO login prompt ───────────────────────────────────────────

log "Waiting for Arch ISO boot (archiso login: ~45-90s)..."
if ! wait_for "archiso login:|login:" 120; then
  pane_output | tail -30
  fail "Arch ISO did not reach login prompt"
fi
ok "Arch ISO booted"

# Log in as root (no password on Arch ISO)
vm_enter "root"
sleep 3

# ── mount host repo via 9p ────────────────────────────────────────────────────

log "Mounting host repo (9p)..."
vm_enter "mkdir -p /host && mount -t 9p -o trans=virtio,version=9p2000.L blk7arch /host"
sleep 3
if ! pane_output | grep -qE "[#$]"; then  # [FIX-T2] unambiguous: match # or $ anywhere on line
  wait_for "[#$]" 15
fi

# Verify installer is accessible
vm_enter "ls /host/BLK7ARCHv1_0.sh && echo '9P_OK'"
sleep 3
if ! wait_for "9P_OK" 15; then
  fail "9p share not accessible"
fi
ok "9p share mounted"

# ── DRY-RUN TEST ─────────────────────────────────────────────────────────────

if [[ "$RUN_DRY" == "true" ]]; then
  log "=== Starting dry-run test ==="
  DRYRUN_MARKER="DRYRUN_COMPLETE_$$"

  vm_enter "bash /host/BLK7ARCHv1_0.sh dry-run \\
    --disk /dev/vda \\
    --hostname ${HOSTNAME} \\
    --username ${USERNAME} \\
    --lv-root-size ${LV_ROOT} \\
    --lv-swap-size ${LV_SWAP} \\
    && echo '${DRYRUN_MARKER}:0' || echo '${DRYRUN_MARKER}:1'"

  log "Waiting for dry-run to complete (~2 min)..."
  if ! wait_for "${DRYRUN_MARKER}" 180; then
    pane_output | tail -40 >> "${LOGFILE}"
    fail "Dry-run did not complete within 3 minutes"
  fi

  DRY_RC=0
  pane_output | grep -qE "${DRYRUN_MARKER}:1" && DRY_RC=1

  if (( DRY_RC == 0 )); then
    ok "DRY-RUN: PASSED"
  else
    warn "DRY-RUN: FAILED"
  fi
  echo "DRY_RUN_RESULT=${DRY_RC}" >> "${LOGFILE}"
fi

# ── CORE-INSTALL TEST ─────────────────────────────────────────────────────────

if [[ "$RUN_INSTALL" == "true" ]]; then
  log "=== Starting core-install test ==="
  INSTALL_MARKER="INSTALL_COMPLETE_$$"

  # Launch install (will prompt for LUKS passphrase then user passphrase)
  # [FIX-T1] Append marker so INSTALL_RC can be set from output instead of relying on timeout
  vm_enter "bash /host/BLK7ARCHv1_0.sh core-install \\
    --disk /dev/vda \\
    --hostname ${HOSTNAME} \\
    --username ${USERNAME} \\
    --lv-root-size ${LV_ROOT} \\
    --lv-swap-size ${LV_SWAP} \\
    --yes \\
    && echo '${INSTALL_MARKER}:0' || echo '${INSTALL_MARKER}:1'"

  # Wait for LUKS passphrase prompt
  log "Waiting for LUKS passphrase prompt..."
  if ! wait_for "Enter new LUKS passphrase" 30; then
    warn "No LUKS passphrase prompt detected — may be already past it"
  fi
  vm_enter "${LUKS_PASS}"

  # Confirm LUKS passphrase
  sleep 2
  if wait_for "Confirm new LUKS passphrase" 15; then
    vm_enter "${LUKS_PASS}"
  fi

  # [FIX-T1] Wait for user/root account password prompt (new in FIX-B1)
  sleep 2
  if wait_for "Enter password for root" 20; then
    vm_enter "${LUKS_PASS}"
    sleep 1
    if wait_for "Confirm password" 10; then
      vm_enter "${LUKS_PASS}"
    fi
  fi

  # Wait for installation to complete (allow up to 40 minutes)
  log "Waiting for installation to complete (up to 40 min)..."

  # Poll every 30s, print progress
  TIMEOUT=2400  # 40 min
  ELAPSED=0
  INSTALL_RC=99
  while (( ELAPSED < TIMEOUT )); do
    sleep 30
    ELAPSED=$(( ELAPSED + 30 ))

    OUT=$(pane_output)

    # Check completion markers
    if echo "$OUT" | grep -qE "${INSTALL_MARKER}:0"; then
      INSTALL_RC=0; break
    elif echo "$OUT" | grep -qE "${INSTALL_MARKER}:1"; then
      INSTALL_RC=1; break
    fi

    # Check for success messages (in case marker was missed)
    if echo "$OUT" | grep -qE "Core installation completed successfully"; then
      INSTALL_RC=0; break
    fi

    # Check for fatal errors
    if echo "$OUT" | grep -qE "\[ERROR\]|cryptsetup: command not found|FAILED"; then
      warn "Possible error detected at ${ELAPSED}s — checking..."
    fi

    # Print last relevant log line every minute
    if (( ELAPSED % 60 == 0 )); then
      LAST=$(echo "$OUT" | grep -E "STEP|OK|ERR|pacstrap|mkinitcpio|grub|chroot" | tail -3)
      log "Progress (~${ELAPSED}s): ${LAST:-<no output yet>}"
    fi
  done

  # Append full log to logfile
  pane_output >> "${LOGFILE}"

  if (( INSTALL_RC == 0 )); then
    ok "CORE-INSTALL: PASSED"
  else
    warn "CORE-INSTALL: did not return clean exit — checking output..."
    # Check if "completed successfully" appeared even without the marker
    if pane_output | grep -qE "Core installation completed successfully"; then
      ok "CORE-INSTALL: PASSED (via success string)"
      INSTALL_RC=0
    else
      warn "CORE-INSTALL: FAILED or timed out"
    fi
  fi
  echo "CORE_INSTALL_RESULT=${INSTALL_RC}" >> "${LOGFILE}"
fi

# ── SUMMARY ──────────────────────────────────────────────────────────────────

log "=== TEST SUMMARY ==="
echo ""
echo "Log file: ${LOGFILE}"
echo ""

if [[ "$RUN_DRY" == "true" ]]; then
  if (( DRY_RC == 0 )); then
    ok "dry-run:     PASSED"
  else
    warn "dry-run:     FAILED"
  fi
fi

if [[ "$RUN_INSTALL" == "true" ]]; then
  if (( INSTALL_RC == 0 )); then
    ok "core-install: PASSED"
  else
    warn "core-install: FAILED"
  fi
fi

echo ""
log "Full output captured in: ${LOGFILE}"
log "VM still running in tmux session '${SESSION}'"
log "  Attach: tmux attach -t ${SESSION}"
log "  Kill:   tmux kill-session -t ${SESSION}"
