#!/usr/bin/env bash
#----------------------------------------------------------------------------
# Project     : ADV7SEC Report Instantiator v1.0
# Description : Create a pre-filled CVE report from ADV7SEC_CVE_Report_Template.md
# Date        : 22/05/2026
# CreatedBy   : ADVAN7 Offensive Security | https://github.com/aopsec
#----------------------------------------------------------------------------
# USAGE:
#   ./new_report.sh --cve CVE-2023-30258 \
#                   --target https://vswitcher.com \
#                   --severity CRITICAL \
#                   --phase 8 \
#                   --scan-dir fuzz_vswitcher.com_20260522_020632
#
#   ./new_report.sh --name "SQLi-login-form" \
#                   --target https://target.com \
#                   --severity HIGH \
#                   --phase "1,2,8"
#
# OPTIONS:
#   --cve CVE-ID       CVE identifier (e.g. CVE-2023-30258). Mutually exclusive with --name.
#   --name SLUG        Custom finding name when no CVE exists (e.g. SQLi-login-form).
#   --target URL       Target URL (must start with http:// or https://).
#   --severity SEV     Severity: CRITICAL, HIGH, MEDIUM, LOW, INFO.
#   --phase N          Phase(s) that found the issue (e.g. 8 or "1,2,8").
#   --scan-dir DIR     adv7FUZZ scan output directory (optional — uses placeholder if absent).
#   --out DIR          Output directory (default: findings/ relative to script location).
#   -h, --help         Show this help.
#
# AUTO-FILLED FIELDS:
#   {{AUTO:date}}         → YYYY-MM-DD (today)
#   {{AUTO:date_compact}} → YYYYMMDD
#   {{AUTO:cve}}          → CVE ID or custom name
#   {{AUTO:target}}       → target URL
#   {{AUTO:host}}         → hostname extracted from URL
#   {{AUTO:severity}}     → severity string
#   {{AUTO:version}}      → adv7FUZZ VERSION (read from adv7FUZZ.sh)
#   {{AUTO:scandir}}      → scan directory or placeholder
#   {{AUTO:phase}}        → phase argument
#   {{AUTO:nvd_url}}      → NVD URL (only when --cve is a real CVE ID)
#----------------------------------------------------------------------------

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="${SCRIPT_DIR}/ADV7SEC_CVE_Report_Template.md"
ADV7FUZZ_SH="${SCRIPT_DIR}/../../adv7FUZZ.sh"

CVE_ID=""
CUSTOM_NAME=""
TARGET_URL=""
SEVERITY=""
PHASE_ARG=""
SCAN_DIR=""
OUT_DIR="${SCRIPT_DIR}/../"   # one level up = findings/

#— Argument parsing ----------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --cve)       CVE_ID="$2";       shift 2 ;;
        --name)      CUSTOM_NAME="$2";  shift 2 ;;
        --target)    TARGET_URL="$2";   shift 2 ;;
        --severity)  SEVERITY="$2";     shift 2 ;;
        --phase)     PHASE_ARG="$2";    shift 2 ;;
        --scan-dir)  SCAN_DIR="$2";     shift 2 ;;
        --out)       OUT_DIR="$2";      shift 2 ;;
        -h|--help)
            grep "^#" "$0" | grep -v "^#!/" | sed 's/^# \{0,\}//'
            exit 0 ;;
        *) echo "[!] Unknown option: $1"; exit 1 ;;
    esac
done

#— Validation ----------------------------------------------------------------
if [[ -z "$CVE_ID" && -z "$CUSTOM_NAME" ]]; then
    echo "[!] Provide --cve CVE-XXXX-XXXXX or --name CUSTOM-FINDING-NAME"
    exit 1
fi
if [[ -n "$CVE_ID" && -n "$CUSTOM_NAME" ]]; then
    echo "[!] --cve and --name are mutually exclusive. Use one."
    exit 1
fi
if [[ -z "$TARGET_URL" ]]; then
    echo "[!] --target is required (e.g. --target https://target.com)"
    exit 1
fi
if ! [[ "$TARGET_URL" =~ ^https?://[^[:space:],]+$ ]]; then
    echo "[!] Invalid target URL: '$TARGET_URL'"
    echo "    Must start with http:// or https://"
    exit 1
fi
if [[ -z "$SEVERITY" ]]; then
    echo "[!] --severity is required: CRITICAL, HIGH, MEDIUM, LOW, INFO"
    exit 1
fi
case "${SEVERITY^^}" in
    CRITICAL|HIGH|MEDIUM|LOW|INFO) SEVERITY="${SEVERITY^^}" ;;
    *) echo "[!] --severity must be: CRITICAL, HIGH, MEDIUM, LOW, or INFO"; exit 1 ;;
esac
if [[ ! -f "$TEMPLATE" ]]; then
    echo "[!] Template not found: $TEMPLATE"
    exit 1
fi

#— Resolve auto-fill values --------------------------------------------------
_date=$(date +%Y-%m-%d)
_date_compact=$(date +%Y%m%d)

# Extract hostname from URL
_host="${TARGET_URL#*//}"
_host="${_host%%/*}"
_host="${_host%%:*}"

# Finding ID (CVE or custom name)
if [[ -n "$CVE_ID" ]]; then
    _finding_id="$CVE_ID"
    # Only build NVD URL for real CVE-XXXX-NNNNN patterns
    if [[ "$CVE_ID" =~ ^CVE-[0-9]{4}-[0-9]+$ ]]; then
        _nvd_url="https://nvd.nist.gov/vuln/detail/${CVE_ID}"
    else
        _nvd_url="[NVD URL — verify CVE ID format]"
    fi
else
    _finding_id="$CUSTOM_NAME"
    _nvd_url="N/A — no CVE assigned"
fi

# Read adv7FUZZ version from sibling adv7FUZZ.sh (if present)
_version="[unknown]"
if [[ -f "$ADV7FUZZ_SH" ]]; then
    _v=$(grep -m1 '^VERSION=' "$ADV7FUZZ_SH" | cut -d'"' -f2)
    [[ -n "$_v" ]] && _version="v${_v}"
fi

# Phase description
_phase_label="${PHASE_ARG:-[phase not specified]}"
case "$PHASE_ARG" in
    0) _phase_label="Phase 0 — Subdomain Enum" ;;
    1) _phase_label="Phase 1 — Fast Recon" ;;
    2) _phase_label="Phase 2 — Extension Scan" ;;
    3) _phase_label="Phase 3 — Combined Scan" ;;
    4) _phase_label="Phase 4 — Recursive" ;;
    5) _phase_label="Phase 5 — Smart Crawl (katana)" ;;
    6) _phase_label="Phase 6 — Parameter Discovery (arjun)" ;;
    7) _phase_label="Phase 7 — API Scanning (ffuf + kiterunner)" ;;
    8) _phase_label="Phase 8 — Nuclei Vulnerability Scan" ;;
esac

# Scan directory
_scandir="${SCAN_DIR:-[scan-dir not provided — pass --scan-dir fuzz_HOST_TIMESTAMP]}"

# Report ID
_report_id="ADV7-${_date_compact}-001"

#— Build output filename -------------------------------------------------------
_safe_host="${_host//[^a-zA-Z0-9._-]/_}"
_safe_id="${_finding_id//[^a-zA-Z0-9._-]/_}"
_outfile="${OUT_DIR}/${_date_compact}_${_safe_id}_${_safe_host}.md"

# Resolve to absolute path
_outfile="$(realpath -m "$_outfile")"
_outdir="$(dirname "$_outfile")"

if [[ ! -d "$_outdir" ]]; then
    echo "[!] Output directory does not exist: $_outdir"
    exit 1
fi

#— Instantiate template -------------------------------------------------------
# sed replacements for {{AUTO:*}} markers.
# Use | as sed delimiter to avoid conflicts with URLs containing /.

sed \
    -e "s|{{AUTO:date_compact}}|${_date_compact}|g" \
    -e "s|{{AUTO:date}}|${_date}|g" \
    -e "s|{{AUTO:cve}}|${_finding_id}|g" \
    -e "s|{{AUTO:target}}|${TARGET_URL}|g" \
    -e "s|{{AUTO:host}}|${_host}|g" \
    -e "s|{{AUTO:severity}}|${SEVERITY}|g" \
    -e "s|{{AUTO:version}}|${_version}|g" \
    -e "s|{{AUTO:scandir}}|${_scandir}|g" \
    -e "s|{{AUTO:phase}}|${_phase_label}|g" \
    -e "s|{{AUTO:nvd_url}}|${_nvd_url}|g" \
    -e "s|ADV7-{{AUTO:date_compact}}-001|${_report_id}|g" \
    "$TEMPLATE" > "$_outfile"

chmod 600 "$_outfile"

#— Summary -------------------------------------------------------------------
echo ""
echo "[+] Report instantiated: $_outfile"
echo "    Report ID  : ${_report_id}"
echo "    Finding    : ${_finding_id}"
echo "    Target     : ${TARGET_URL}"
echo "    Host       : ${_host}"
echo "    Severity   : ${SEVERITY}"
echo "    Tool ver   : ${_version}"
echo "    Phase      : ${_phase_label}"
echo "    Scan dir   : ${_scandir}"
echo "    NVD URL    : ${_nvd_url}"
echo ""
echo "    Next: fill all [PLACEHOLDER] sections in the report."
echo "    Edit: ${_outfile}"
echo ""
