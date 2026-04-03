#!/usr/bin/env bash
# tests/vm/setup.sh — create test VM artifacts for BLK7ARCHv1_0.sh
# Run once before start.sh. Safe to re-run; skips existing disk.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACTS="${SCRIPT_DIR}/artifacts"
DISK="${ARTIFACTS}/test-disk.qcow2"
OVMF_VARS="${ARTIFACTS}/OVMF_VARS.fd"
OVMF_CODE="/usr/share/OVMF/OVMF_CODE.fd"
OVMF_VARS_SRC="/usr/share/OVMF/OVMF_VARS.fd"
DISK_SIZE="80G"
ISO="/var/lib/libvirt/images/archlinux-x86_64.iso"

# --- Preflight ----------------------------------------------------------------
if [[ ! -f "$OVMF_CODE" ]]; then
  echo "[ERROR] OVMF firmware not found at $OVMF_CODE" >&2
  echo "        Install with: sudo dnf install edk2-ovmf   # Fedora" >&2
  exit 1
fi
if [[ ! -f "$ISO" ]]; then
  echo "[ERROR] Arch ISO not found at $ISO" >&2
  echo "        Download: curl -L -o '$ISO' 'https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso'" >&2
  exit 1
fi
if [[ ! -e /dev/kvm ]]; then
  echo "[ERROR] /dev/kvm not available. Enable KVM or run: sudo modprobe kvm_intel" >&2
  exit 1
fi

mkdir -p "$ARTIFACTS"

# --- OVMF vars (writable per-VM copy) ----------------------------------------
if [[ ! -f "$OVMF_VARS" ]]; then
  cp "$OVMF_VARS_SRC" "$OVMF_VARS"
  echo "[OK] Copied OVMF_VARS.fd → artifacts/"
else
  echo "[OK] OVMF_VARS.fd already exists (skipping)"
fi

# --- Virtual disk ------------------------------------------------------------
if [[ ! -f "$DISK" ]]; then
  qemu-img create -f qcow2 "$DISK" "$DISK_SIZE"
  echo "[OK] Created ${DISK_SIZE} qcow2 disk → artifacts/test-disk.qcow2"
else
  echo "[OK] Disk already exists: $(qemu-img info --output=human "$DISK" | grep 'virtual size')"
  echo "     To recreate: rm ${DISK} && bash setup.sh"
fi

echo ""
echo "Setup complete. Run ./start.sh [--tui|--headless] to boot the VM."
echo ""
echo "Inside the VM, access the installer at: /host/BLK7ARCHv1_0.sh"
echo "  mount -t 9p -o trans=virtio,version=9p2000.L blk7arch /host"
echo ""
echo "Target disk inside VM: /dev/vda"
echo ""
echo "Quick test commands (run inside VM after mounting /host):"
echo "  # Dry-run (no disk writes):"
echo "  bash /host/BLK7ARCHv1_0.sh dry-run --disk /dev/vda --hostname archtest --username testuser --lv-root-size 40G --lv-swap-size 4G"
echo ""
echo "  # Full core-install (destructive — erases /dev/vda):"
echo "  bash /host/BLK7ARCHv1_0.sh core-install --disk /dev/vda --hostname archtest --username testuser --lv-root-size 40G --lv-swap-size 4G --yes"
echo ""
echo "  # TUI wizard:"
echo "  bash /host/BLK7ARCHv1_0.sh --tui"
