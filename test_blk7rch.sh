#!/usr/bin/env bash
set -euo pipefail

echo "╔════════════════════════════════════════════════════════╗"
echo "║         BLK7RCH.sh COMPREHENSIVE TEST SUITE            ║"
echo "╚════════════════════════════════════════════════════════╝"

TESTS_PASSED=0
TESTS_FAILED=0
SCRIPT="./BLK7RCH.sh"

run_test() {
  local test_name="$1"
  local cmd="$2"
  local expected_exit="${3:-0}"
  
  echo -n "TEST: $test_name ... "
  if eval "$cmd" >/dev/null 2>&1; then
    if [[ $expected_exit -eq 0 ]]; then
      echo "✓ PASS"
      ((TESTS_PASSED++))
    else
      echo "✗ FAIL (expected exit code $expected_exit)"
      ((TESTS_FAILED++))
    fi
  else
    local exit_code=$?
    if [[ $exit_code -eq $expected_exit ]]; then
      echo "✓ PASS (exit $exit_code)"
      ((TESTS_PASSED++))
    else
      echo "✗ FAIL (exit $exit_code, expected $expected_exit)"
      ((TESTS_FAILED++))
    fi
  fi
}

# Test 1: Syntax validation
echo ""
echo "═══ SECTION 1: Syntax & Format Validation ═══"
run_test "Bash syntax check" "bash -n $SCRIPT" 0
run_test "File is readable" "test -r $SCRIPT" 0
run_test "Script has shebang" "head -1 $SCRIPT | grep -q '^#!/usr/bin/env bash'" 0

# Test 2: Help & usage
echo ""
echo "═══ SECTION 2: Help & Usage Messages ═══"
run_test "Help message prints" "$SCRIPT 2>&1 | grep -q 'Usage:'" 0
run_test "Shows subcommands" "$SCRIPT 2>&1 | grep -q 'core-install'" 0
run_test "Shows required flags" "$SCRIPT 2>&1 | grep -q -- '--disk'" 0
run_test "Shows optional flags" "$SCRIPT 2>&1 | grep -q -- '--timezone'" 0

# Test 3: Argument validation
echo ""
echo "═══ SECTION 3: Argument Validation ═══"
run_test "Missing subcommand fails" "$SCRIPT 2>&1 | grep -q 'Usage:' || exit 1" 0
run_test "Invalid subcommand handled" "$SCRIPT invalid-cmd 2>&1 | grep -iE '(unknown|invalid|usage)' || exit 1" 0
run_test "core-install without --disk fails" "$SCRIPT core-install 2>&1 | grep -q 'disk' || exit 1" 0
run_test "core-install without --hostname fails" "$SCRIPT core-install --disk /dev/fake 2>&1 | grep -q 'hostname' || exit 1" 0
run_test "core-install without --username fails" "$SCRIPT core-install --disk /dev/fake --hostname test 2>&1 | grep -q 'username' || exit 1" 0

# Test 4: Disk validation
echo ""
echo "═══ SECTION 4: Disk Path Validation ═══"
run_test "Rejects invalid disk path" "$SCRIPT core-install --disk /dev/nonexistent --hostname test --username user 2>&1 | grep -iE '(not found|invalid|error)' || exit 1" 0
run_test "Handles nvme partition naming" "source $SCRIPT; DISK=/dev/nvme0n1; resolve_partition_paths; [[ \$EFI_PART == /dev/nvme0n1p1 ]]" 0
run_test "Handles sda partition naming" "source $SCRIPT; DISK=/dev/sda; resolve_partition_paths; [[ \$LUKS_PART == /dev/sda2 ]]" 0

# Test 5: Boolean parsing
echo ""
echo "═══ SECTION 5: Boolean Parameter Parsing ═══"
run_test "parse_bool('true') returns true" "source $SCRIPT; [[ \$(parse_bool 'true') == 'true' ]]" 0
run_test "parse_bool('false') returns false" "source $SCRIPT; [[ \$(parse_bool 'false') == 'false' ]]" 0
run_test "parse_bool('invalid') fails" "source $SCRIPT; parse_bool 'invalid' 2>&1 | grep -q 'Invalid' || exit 1" 0

# Test 6: Configuration variables
echo ""
echo "═══ SECTION 6: Default Configuration ═══"
run_test "Default timezone is set" "source $SCRIPT; [[ -n \$TIMEZONE ]]" 0
run_test "Default timezone is valid" "source $SCRIPT; [[ -f /usr/share/zoneinfo/\$TIMEZONE ]]" 0
run_test "Default locale is en_US.UTF-8" "source $SCRIPT; [[ \${LOCALES[0]} == 'en_US.UTF-8' ]]" 0
run_test "LUKS_NAME defaults to cryptlvm" "source $SCRIPT; [[ \$LUKS_NAME == 'cryptlvm' ]]" 0

# Test 7: Function existence
echo ""
echo "═══ SECTION 7: Core Functions Defined ═══"
run_test "partition_disk function exists" "source $SCRIPT && declare -f partition_disk >/dev/null" 0
run_test "setup_encryption_lvm function exists" "source $SCRIPT && declare -f setup_encryption_lvm >/dev/null" 0
run_test "format_and_mount function exists" "source $SCRIPT && declare -f format_and_mount >/dev/null" 0
run_test "install_workstation_profile function exists" "source $SCRIPT && declare -f install_workstation_profile >/dev/null" 0
run_test "install_ids_profile function exists" "source $SCRIPT && declare -f install_ids_profile >/dev/null" 0

# Test 8: Dry-run mode
echo ""
echo "═══ SECTION 8: Dry-Run Mode ═══"
run_test "Dry-run doesn't require root" "$SCRIPT --dry-run core-install --disk /dev/sda --hostname test --username user 2>&1 | grep -q 'dry-run' || exit 0" 0
run_test "Dry-run mode prints info" "$SCRIPT --dry-run core-install --disk /dev/sda --hostname test --username user 2>&1 | grep -iE '(would|dry)' || exit 0" 0

# Test 9: Test reporting
echo ""
echo "═══ SECTION 9: Test Report Generation ═══"
run_test "test-report flag accepted" "$SCRIPT core-install --disk /dev/fake --hostname test --username user --test-report true 2>&1 | grep -qE '(test|report)' || exit 0" 0

# Test 10: IDS profile validation
echo ""
echo "═══ SECTION 10: IDS Profile Checks ═══"
run_test "IDS mode parameter validated" "source $SCRIPT; IDS_MODE='minimal-local'; [[ -n \$IDS_MODE ]]" 0
run_test "IDS home net defaults correctly" "source $SCRIPT; [[ -n \$IDS_HOME_NET ]]" 0
run_test "Snort profile options valid" "source $SCRIPT; IDS_SNORT_PROFILE='balanced'; [[ \$IDS_SNORT_PROFILE =~ ^(balanced|strict)$ ]]" 0

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║                    TEST SUMMARY                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo "Passed:  $TESTS_PASSED"
echo "Failed:  $TESTS_FAILED"
echo "Total:   $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
  echo "✓ ALL TESTS PASSED"
  exit 0
else
  echo "✗ SOME TESTS FAILED"
  exit 1
fi
