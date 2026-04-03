#!/usr/bin/env bash
# tests/vm/start.sh — boot BLK7ARCH test VM
#
# Usage:
#   ./start.sh              # interactive mode: GTK window + serial console
#   ./start.sh --tui        # same, optimised label for TUI testing
#   ./start.sh --headless   # no display: serial console only (SSH on 127.0.0.1:2222)
#   ./start.sh --resume     # boot from disk only (skip ISO, test installed system)
#
# The host repo root is shared into the VM as a 9p filesystem (tag: blk7arch).
# Inside the VM:
#   mount -t 9p -o trans=virtio,version=9p2000.L blk7arch /host
#   bash /host/BLK7ARCHv1_0.sh ...
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ARTIFACTS="${SCRIPT_DIR}/artifacts"
DISK="${ARTIFACTS}/test-disk.qcow2"
OVMF_VARS="${ARTIFACTS}/OVMF_VARS.fd"
OVMF_CODE="/usr/share/OVMF/OVMF_CODE.fd"
ISO="/var/lib/libvirt/images/archlinux-x86_64.iso"

MODE="interactive"
BOOT_ORDER="dc"   # d=cdrom first, c=disk second

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tui)       MODE="tui"       ;;
    --headless)  MODE="headless"  ;;
    --resume)    MODE="resume"; BOOT_ORDER="c" ;;
    *) echo "[ERROR] Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

# --- Preflight ----------------------------------------------------------------
if [[ ! -f "$DISK" || ! -f "$OVMF_VARS" ]]; then
  echo "[ERROR] Artifacts missing. Run ./setup.sh first." >&2
  exit 1
fi

# --- Build QEMU command -------------------------------------------------------
QEMU_ARGS=(
  qemu-system-x86_64
  -enable-kvm
  -cpu host
  -m 4G
  -smp 4

  # UEFI firmware (required by installer)
  -drive "if=pflash,format=raw,readonly=on,file=${OVMF_CODE}"
  -drive "if=pflash,format=raw,file=${OVMF_VARS}"

  # Target disk (virtio for performance)
  -drive "file=${DISK},if=virtio,format=qcow2,cache=writeback"

  # Network: user-mode NAT; SSH forwarded to host:2222
  -netdev "user,id=net0,hostfwd=tcp::2222-:22"
  -device "virtio-net-pci,netdev=net0"

  # Host→VM filesystem share (9p): installer accessible at /host inside VM
  -virtfs "local,path=${REPO_ROOT},mount_tag=blk7arch,security_model=mapped-xattr,id=blk7arch"

  # Serial console (always enabled; --headless uses it as primary I/O)
  -serial "mon:stdio"

  -name "BLK7ARCH-test-${MODE}"
)

# Attach ISO unless resuming from installed disk
if [[ "$MODE" != "resume" ]]; then
  QEMU_ARGS+=(
    -drive "file=${ISO},media=cdrom,readonly=on,if=ide"
    -boot "order=${BOOT_ORDER}"
  )
fi

# Display
case "$MODE" in
  interactive|tui|resume)
    QEMU_ARGS+=(-display gtk,gl=off)
    ;;
  headless)
    QEMU_ARGS+=(-display none -nographic)
    echo "[INFO] Headless mode. Serial console on stdin/stdout."
    echo "       SSH into VM:  ssh -p 2222 root@127.0.0.1"
    ;;
esac

# --- Print instructions -------------------------------------------------------
cat <<'INSTRUCTIONS'
=========================================================
 BLK7ARCH Test VM — Quick Reference
=========================================================
 After boot (Arch ISO live shell):

   # 1. Mount host repo
   mkdir -p /host
   mount -t 9p -o trans=virtio,version=9p2000.L blk7arch /host

   # 2a. Dry-run (safe, no disk writes)
   bash /host/BLK7ARCHv1_0.sh dry-run \
     --disk /dev/vda \
     --hostname archtest \
     --username testuser \
     --lv-root-size 40G \
     --lv-swap-size 4G

   # 2b. Full install (DESTRUCTIVE — erases /dev/vda)
   bash /host/BLK7ARCHv1_0.sh core-install \
     --disk /dev/vda \
     --hostname archtest \
     --username testuser \
     --lv-root-size 40G \
     --lv-swap-size 4G \
     --yes

   # 2c. TUI wizard
   pacman -Sy libnewt --noconfirm
   bash /host/BLK7ARCHv1_0.sh --tui

   # 3. After install: run validation
   bash /host/BLK7ARCHv1_0.sh validate

=========================================================
 To exit QEMU:  Ctrl-A X  (headless)  or  close window
=========================================================
INSTRUCTIONS

# --- Launch -------------------------------------------------------------------
echo "[INFO] Starting QEMU (mode=${MODE})..."
exec "${QEMU_ARGS[@]}"
