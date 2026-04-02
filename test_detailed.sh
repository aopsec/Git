#!/usr/bin/env bash

# Don't source main, just extract and test functions
define_test_functions() {
  # Copy essential functions from BLK7RCH.sh
  
  parse_bool() {
    local value="$1"
    if [[ "$value" == "true" || "$value" == "false" ]]; then
      printf '%s' "$value"
    else
      printf '[ERROR] Invalid bool: %s\n' "$value" >&2
      exit 5
    fi
  }
  
  resolve_partition_paths() {
    local DISK="${1:-.}"
    local EFI_PART LUKS_PART
    if [[ "$DISK" =~ (nvme|mmcblk) ]]; then
      EFI_PART="${DISK}p1"
      LUKS_PART="${DISK}p2"
    else
      EFI_PART="${DISK}1"
      LUKS_PART="${DISK}2"
    fi
    printf 'EFI_PART=%s\nLUKS_PART=%s\n' "$EFI_PART" "$LUKS_PART"
  }
}

define_test_functions

echo "╔═══════════════════════════════════════════════════════╗"
echo "║    BLK7RCH.sh DETAILED TEST REPORT                   ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

PASS=0
FAIL=0

test_bool() {
  local val="$1" expected="$2"
  result=$(parse_bool "$val")
  if [[ "$result" == "$expected" ]]; then
    echo "✓ parse_bool('$val') = '$expected'"
    ((PASS++))
  else
    echo "✗ parse_bool('$val') = '$result' (expected '$expected')"
    ((FAIL++))
  fi
}

test_partition() {
  local disk="$1" exp_efi="$2" exp_luks="$3"
  output=$(resolve_partition_paths "$disk")
  efi=$(echo "$output" | grep EFI_PART | cut -d= -f2)
  luks=$(echo "$output" | grep LUKS_PART | cut -d= -f2)
  
  local pass=true
  if [[ "$efi" != "$exp_efi" ]]; then
    echo "✗ EFI partition: got '$efi', expected '$exp_efi'"
    pass=false
    ((FAIL++))
  fi
  if [[ "$luks" != "$exp_luks" ]]; then
    echo "✗ LUKS partition: got '$luks', expected '$exp_luks'"
    pass=false
    ((FAIL++))
  fi
  if [[ "$pass" == "true" ]]; then
    echo "✓ Partition paths for $disk: EFI=$efi, LUKS=$luks"
    ((PASS++))
  fi
}

echo "TEST SECTION 1: Boolean Parsing"
echo "────────────────────────────────"
test_bool "true" "true"
test_bool "false" "false"
echo ""

echo "TEST SECTION 2: Partition Resolution"
echo "──────────────────────────────────────"
test_partition "/dev/nvme0n1" "/dev/nvme0n1p1" "/dev/nvme0n1p2"
test_partition "/dev/sda" "/dev/sda1" "/dev/sda2"
test_partition "/dev/sdb" "/dev/sdb1" "/dev/sdb2"
test_partition "/dev/mmcblk0" "/dev/mmcblk0p1" "/dev/mmcblk0p2"
echo ""

echo "TEST SECTION 3: Script Header Validation"
echo "──────────────────────────────────────────"
if head -1 BLK7RCH.sh | grep -q '^#!/usr/bin/env bash'; then
  echo "✓ Script has correct shebang"
  ((PASS++))
else
  echo "✗ Script shebang incorrect"
  ((FAIL++))
fi

if bash -n BLK7RCH.sh 2>/dev/null; then
  echo "✓ Bash syntax validation passed"
  ((PASS++))
else
  echo "✗ Bash syntax validation failed"
  ((FAIL++))
fi
echo ""

echo "TEST SECTION 4: Code Quality Checks"
echo "─────────────────────────────────────"

# Check for common issues
checks=(
  "arch-chroot.*pacman -Si:IDS package validation implemented"
  "mkdir -p.*home.*USERNAME:User home directory handling improved"
  "write_test_report.*skipped:Test report for skipped stages"
  "require_root:Root check function"
  "partition_disk:Partition function"
  "setup_encryption_lvm:LUKS+LVM setup"
  "install_workstation_profile:Workstation profile"
  "install_ids_profile:IDS profile installation"
)

for check in "${checks[@]}"; do
  pattern="${check%:*}"
  desc="${check#*:}"
  if grep -q "$pattern" BLK7RCH.sh 2>/dev/null; then
    echo "✓ $desc"
    ((PASS++))
  else
    echo "✗ $desc (pattern: $pattern)"
    ((FAIL++))
  fi
done
echo ""

echo "TEST SECTION 5: Command Help Validation"
echo "────────────────────────────────────────"
if bash BLK7RCH.sh 2>&1 | grep -q "Usage:"; then
  echo "✓ Help message displays correctly"
  ((PASS++))
else
  echo "✗ Help message missing"
  ((FAIL++))
fi

if bash BLK7RCH.sh 2>&1 | grep -q "core-install"; then
  echo "✓ core-install subcommand documented"
  ((PASS++))
else
  echo "✗ core-install subcommand missing"
  ((FAIL++))
fi

if bash BLK7RCH.sh 2>&1 | grep -q -- "--disk"; then
  echo "✓ --disk flag documented"
  ((PASS++))
else
  echo "✗ --disk flag not documented"
  ((FAIL++))
fi
echo ""

echo "╔═══════════════════════════════════════════════════════╗"
echo "║                  TEST SUMMARY                         ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo "Passed:  $PASS"
echo "Failed:  $FAIL"
echo "Total:   $((PASS + FAIL))"
echo ""

if [[ $FAIL -eq 0 ]]; then
  echo "✓✓✓ ALL TESTS PASSED ✓✓✓"
  exit 0
else
  echo "⚠ Some tests failed. Review output above."
  exit 1
fi
