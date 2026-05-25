#!/usr/bin/env bash
#----------------------------------------------------------------------------
# Project     : adv7FUZZ v0.1.5
# Description : Phased web content discovery for authorized pentesting
# Date        : 23/05/2026
# CreatedBy   : ADVAN7 Offensive Security | https://github.com/aopsec
#----------------------------------------------------------------------------
# PHASES:
#   0 — Subdomain Enum : amass passive enum (optional — skip if amass absent)
#   1 — Fast Recon     : common.txt, no extensions, max threads
#   2 — Extension Scan : big.txt + web extensions
#   3 — Combined Scan  : combined wordlist + web extensions
#   4 — Recursive      : dir-like 200s from Phase 1 → deep crawl
#   5 — Smart Crawl    : katana JS-aware spider (optional)
#   6 — Param Discovery: arjun on confirmed endpoints (optional)
#   7 — API Scanning   : ffuf API wordlist + kiterunner routes (optional)
#   8 — Nuclei Scan    : template vuln scan on all confirmed hits (optional)
#
# STATUS CODES captured (follow-redirects OFF by design):
#   200,201,204      — direct hits
#   301,302,307,308  — redirects (Location header extracted in report)
#   401,403,405      — auth walls / method restrictions
#   Auto-calibration (-ac) filters uniform WAF/CDN responses automatically.
#
# WHY follow-redirects is disabled:
#   Following hides the original triggering path. /admin → 301 → /login
#   records /login (known) instead of /admin (new finding). Redirect
#   destinations are extracted from JSON and reported separately.
#
# EVASION (default ON, all flags optional):
#   Tor egress via torsocks — hard abort if Tor unreachable (use --no-tor)
#   Random User-Agent from builtin pool of 8 realistic browsers
#   Cookie mode: interactive prompt at startup (skip: --cookie random|custom)
#
# ROTATION (auto Tor circuit rotation on block detection):
#   Pre-phase canary: exit IP logged + lightweight HEAD to target before each phase
#   On block detected: sudo systemctl restart tor  (interactive — enter sudo password)
#   Fallback: 65s wait for natural Tor circuit rotation (~10 min cycle)
#   Phase 2/3 split into chunks of --circuit-size rows; canary fires between chunks
#   Disable: --no-canary  |  Tune: --tor-retries N  --circuit-size N
#
# USAGE:
#   ./adv7FUZZ.sh [OPTIONS]
#   ./adv7FUZZ.sh -u https://target.com
#
# OPTIONS:
#   -u URL            Target URL (e.g. https://target.com)
#   -f FILE           File of target URLs — one per line, # = comment, blank skipped
#   -w FILE           Override big.txt wordlist path
#   -x PROXY          HTTP/SOCKS proxy (e.g. http://127.0.0.1:8080 for Burp)
#   -t THREADS        Base concurrent threads (default: 50)
#   --burp            Proxy ffuf via Burp Suite on 127.0.0.1:8080
#                     Disables torsocks for ffuf (torsocks blocks 127.0.0.1).
#                     For Tor anonymity: configure Burp upstream SOCKS → 127.0.0.1:9050
#   --burp-port N     Burp listen port (default: 8080)
#   --no-tor          Disable torsocks egress (use direct IP or -x/-burp proxy)
#   --ua STRING       Force specific User-Agent string
#   --cookie random   Skip prompt — use generated browser cookies
#   --cookie custom   Skip prompt — ask only for cookie paste
#   --no-canary       Skip pre-phase and inter-chunk Tor canary checks
#   --tor-retries N   Max rotation attempts per phase (default: 3)
#   --circuit-size N  Wordlist rows per Tor circuit chunk (default: 50000)
#   --phase N         Run only phase N (0-8)
#   --skip-phase0     Skip amass subdomain enum (run Phases 1–8 only)
#   --scan-subdomains After Phase 0, run Phases 1–8 on every discovered subdomain
#   --katana-depth N  Katana crawl depth (default: 3)
#   --arjun-max N     Max endpoints for arjun (default: 15)
#   --nuclei-tags T   Nuclei tags (default: cve,misconfig,exposure,tech,api)
#   --oob URL         interactsh server URL for OAST callbacks in Phase 8 (optional)
#   --no-nuclei       Skip Phase 8 nuclei scan entirely
#   --recurse-redirects  Phase 4: also recurse into 301/302/403 dirs (use with auth sessions)
#   --no-ac           Disable ffuf auto-calibration (-ac) — required when all unauth requests
#                     return uniform redirects (e.g. app redirects everything to /login)
#   --dry-run         Print commands without executing
#   -h, --help        Show this help
#----------------------------------------------------------------------------

set -uo pipefail   # no -e: phases may fail independently

VERSION="0.1.5"

_CLEANUP_FILES=()
_cleanup_tmp() {
    if [[ ${#_CLEANUP_FILES[@]} -gt 0 ]]; then
        rm -f "${_CLEANUP_FILES[@]}" 2>/dev/null || true
    fi
}
trap _cleanup_tmp EXIT INT TERM

TOR_MAX_RETRIES=3
TOR_MAX_REQ_PER_CIRCUIT=50000   # wordlist rows per circuit chunk (Phase 2/3)
TOR_CANARY_TIMEOUT=15           # curl timeout for canary requests (seconds)
TOR_WAIT_AFTER_RESTART=12       # seconds to wait after systemctl restart tor
USE_CANARY=true
KATANA_DEPTH=3
ARJUN_MAX=15
NUCLEI_TAGS="cve,misconfig,exposure,tech,api"
OOB_SERVER=""
RECURSE_REDIRECTS=false
NO_AC=false
SKIP_PHASE0=false
NO_NUCLEI=false
MC="200,201,204,301,302,307,308,401,403,405"
EXTS=".php,.html,.txt,.bak,.zip,.sql,.conf,.old,.jar,.json,.xml,.env,.log"
BURP_MODE=false
BURP_PORT=8080
TARGETS_FILE=""
SCAN_SUBDOMAINS=false

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

#— Defaults ------------------------------------------------------------------
USE_TOR=true
UA=""
COOKIE_STRING=""
COOKIE_MODE=""
TARGET=""
PROXY=""
THREADS=50
DRY_RUN=false
ONLY_PHASE=""

WORDLIST="/home/aops/OPia/Git/wordlists/SecLists/Discovery/Web-Content/big.txt"
COMMON="/home/aops/OPia/Git/wordlists/SecLists/Discovery/Web-Content/common.txt"
COMBINED="/home/aops/OPia/Git/wordlists/SecLists/Discovery/Web-Content/combined_words.txt"
API_WL="/home/aops/OPia/Git/wordlists/SecLists/Discovery/Web-Content/api/objects.txt"

#— Argument parsing ----------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -u) TARGET="$2";      shift 2 ;;
        -w) WORDLIST="$2";    shift 2 ;;
        -x) PROXY="$2";       shift 2 ;;
        -t) THREADS="$2";     shift 2 ;;
        --no-tor)       USE_TOR=false;                  shift ;;
        --ua)           UA="$2";                        shift 2 ;;
        --cookie)       COOKIE_MODE="$2";               shift 2 ;;
        --no-canary)    USE_CANARY=false;               shift ;;
        --tor-retries)  TOR_MAX_RETRIES="$2";           shift 2 ;;
        --circuit-size) TOR_MAX_REQ_PER_CIRCUIT="$2";  shift 2 ;;
        --phase)        ONLY_PHASE="$2";                shift 2 ;;
        --skip-phase0)  SKIP_PHASE0=true;               shift ;;
        --katana-depth) KATANA_DEPTH="$2";              shift 2 ;;
        --arjun-max)    ARJUN_MAX="$2";                 shift 2 ;;
        --nuclei-tags)  NUCLEI_TAGS="$2";               shift 2 ;;
        --oob)              OOB_SERVER="$2";            shift 2 ;;
        --oob=*)            OOB_SERVER="${1#*=}";       shift ;;
        --recurse-redirects) RECURSE_REDIRECTS=true;   shift ;;
        --no-ac)            NO_AC=true;                 shift ;;
        --no-nuclei)        NO_NUCLEI=true;             shift ;;
        --burp)         BURP_MODE=true;                 shift ;;
        --burp-port)    BURP_PORT="$2";                 shift 2 ;;
        -f)             TARGETS_FILE="$2";              shift 2 ;;
        --scan-subdomains) SCAN_SUBDOMAINS=true;        shift ;;
        --dry-run)      DRY_RUN=true;                   shift ;;
        -h|--help)
            grep "^#" "$0" | grep -v "^#!/" | sed 's/^# \{0,\}//'
            exit 0 ;;
        *) echo "[!] Unknown option: $1"; exit 1 ;;
    esac
done

#— Numeric flag validation ---------------------------------------------------
if ! [[ "$TOR_MAX_REQ_PER_CIRCUIT" =~ ^[1-9][0-9]*$ ]]; then
    echo "[!] --circuit-size must be a positive integer (got: $TOR_MAX_REQ_PER_CIRCUIT)"
    exit 1
fi
if ! [[ "$THREADS" =~ ^[1-9][0-9]*$ ]]; then
    echo "[!] -t threads must be a positive integer (got: $THREADS)"
    exit 1
fi
if ! [[ "$TOR_MAX_RETRIES" =~ ^[0-9]+$ ]]; then
    echo "[!] --tor-retries must be a non-negative integer (got: $TOR_MAX_RETRIES)"
    exit 1
fi
if ! [[ "$ARJUN_MAX" =~ ^[1-9][0-9]*$ ]]; then
    echo "[!] --arjun-max must be a positive integer (got: $ARJUN_MAX)"
    exit 1
fi
if ! [[ "$KATANA_DEPTH" =~ ^[1-9][0-9]*$ ]]; then
    echo "[!] --katana-depth must be a positive integer (got: $KATANA_DEPTH)"
    exit 1
fi
if ! [[ "$BURP_PORT" =~ ^[1-9][0-9]*$ ]] || [[ "$BURP_PORT" -gt 65535 ]]; then
    echo "[!] --burp-port must be 1–65535 (got: $BURP_PORT)"
    exit 1
fi
if [[ -n "$TARGET" && -n "$TARGETS_FILE" ]]; then
    echo "[!] -u and -f are mutually exclusive. Use one or the other."
    exit 1
fi
# Auto-detect: if -u received a file path rather than a URL, route to -f semantics
if [[ -n "$TARGET" && ! "$TARGET" =~ ^https?:// && -f "$TARGET" ]]; then
    echo "[*] Auto-detected scope file via -u — switching to batch mode: $TARGET"
    TARGETS_FILE="$TARGET"
    TARGET=""
fi
if [[ -n "$ONLY_PHASE" ]]; then
    if ! [[ "$ONLY_PHASE" =~ ^[0-8]$ ]]; then
        echo "[!] --phase must be 0-8 (got: $ONLY_PHASE)"
        exit 1
    fi
    if $SKIP_PHASE0 && [[ "$ONLY_PHASE" == "0" ]]; then
        echo "[!] --skip-phase0 and --phase 0 are mutually exclusive"
        exit 1
    fi
    if $SCAN_SUBDOMAINS; then
        echo "[!] Warning: --scan-subdomains is ignored when --phase is set"
    fi
fi

#— Burp mode: set PROXY (fed into BASE_FFUF via existing -x handling) --------
if $BURP_MODE; then PROXY="http://127.0.0.1:${BURP_PORT}"; fi

#— Dependency check ----------------------------------------------------------
for tool in ffuf jq curl; do
    if ! command -v "$tool" &>/dev/null; then
        echo "[!] Error: $tool not found. Install it first."
        exit 1
    fi
done
if $USE_TOR && ! command -v torsocks &>/dev/null; then
    echo "[!] Error: torsocks not found. Arch: pacman -S torsocks  |  or pass --no-tor"
    exit 1
fi

#— Optional tool availability (missing = that phase skipped, not fatal) ------
HAS_AMASS=false;    command -v amass      &>/dev/null && HAS_AMASS=true
HAS_KATANA=false;   command -v katana     &>/dev/null && HAS_KATANA=true
HAS_ARJUN=false;    command -v arjun      &>/dev/null && HAS_ARJUN=true
HAS_KR=false;       command -v kiterunner &>/dev/null && HAS_KR=true
HAS_NUCLEI=false;   command -v nuclei     &>/dev/null && HAS_NUCLEI=true

#— Tor pre-flight (hard abort — no silent IP leak) ---------------------------
if $USE_TOR; then
    if ! ss -tlnp 2>/dev/null | grep -q "127.0.0.1:9050"; then
        echo "[!] Tor SOCKS not listening on 127.0.0.1:9050"
        echo "    Start Tor : systemctl start tor"
        echo "    Skip Tor  : pass --no-tor"
        exit 1
    fi
fi

#— Helper: generate realistic browser cookies --------------------------------
gen_random_cookies() {
    local sid ga_uid ga_ts gid_ts
    sid=$(openssl rand -hex 16)
    ga_uid=$(shuf -i 100000000-999999999 -n1)
    ga_ts=$(date +%s)
    gid_ts=$(shuf -i 100000000-999999999 -n1)
    echo "PHPSESSID=${sid}; _ga=GA1.2.${ga_uid}.${ga_ts}; _gid=GA1.2.${gid_ts}.${ga_ts}"
}

#— Helper: cookie mode selection (interactive or via --cookie flag) ----------
select_cookies() {
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

#— Build target list ---------------------------------------------------------
declare -a TARGET_LIST=()

# Interactive prompt when neither -u nor -f was given
if [[ -z "$TARGETS_FILE" && -z "$TARGET" ]]; then
    read -rp "Insert Target URL or scope file path... ># " TARGET
    TARGET="${TARGET//[[:space:]]/}"    # strip accidental leading/trailing spaces
    # Auto-detect: file path typed at the prompt → batch mode
    if [[ -n "$TARGET" && ! "$TARGET" =~ ^https?:// && -f "$TARGET" ]]; then
        echo "[*] Auto-detected scope file — batch mode: $TARGET"
        TARGETS_FILE="$TARGET"
        TARGET=""
    fi
fi

if [[ -n "$TARGETS_FILE" ]]; then
    [[ ! -f "$TARGETS_FILE" ]] && { echo "[!] Targets file not found: $TARGETS_FILE"; exit 1; }
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _line="${_line%%#*}"                   # strip inline comments
        _line="${_line//[[:space:]]/}"         # trim all whitespace (pure bash, no subprocess)
        [[ -z "$_line" ]] && continue
        if [[ "$_line" =~ ^https?://[^[:space:],]+$ ]]; then
            TARGET_LIST+=("$_line")
        else
            echo "[!] Skipping invalid URL in file: '$_line'"
        fi
    done < "$TARGETS_FILE"
    [[ ${#TARGET_LIST[@]} -eq 0 ]] && { echo "[!] No valid URLs in $TARGETS_FILE"; exit 1; }
else
    [[ -z "$TARGET" ]] && { echo "[!] No URL provided. Aborting."; exit 1; }
    if ! [[ "$TARGET" =~ ^https?://[^[:space:],]+$ ]]; then
        echo "[!] Invalid target URL: '$TARGET'"
        echo "    Must start with http:// or https:// and contain no spaces or commas."
        echo "    Example: https://target.com  or  http://target.com:8080/path"
        echo "    Tip: To scan from a scope file, pass the .txt path (e.g. /home/aops/scope.txt)"
        exit 1
    fi
    TARGET_LIST=("$TARGET")
fi

#— Authorization confirmation ------------------------------------------------
echo ""
echo "  [!] AUTHORIZATION REQUIRED"
if [[ ${#TARGET_LIST[@]} -eq 1 ]]; then
    echo "      Target : ${TARGET_LIST[0]}"
    echo "      You must have explicit written permission to test this target."
    echo ""
    read -rp "  Confirm you are authorized to test ${TARGET_LIST[0]} [yes/N] > " AUTH
else
    echo "      Targets file : $TARGETS_FILE (${#TARGET_LIST[@]} targets)"
    echo "      You must have explicit written permission to test ALL listed targets."
    echo ""
    read -rp "  Confirm authorization for all ${#TARGET_LIST[@]} targets [yes/N] > " AUTH
fi
[[ "${AUTH,,}" == "yes" ]] || { echo "[*] Aborted — authorization not confirmed."; exit 0; }

#— Cookie selection ----------------------------------------------------------
select_cookies

#— User-Agent resolution (random from pool if not overridden by --ua) --------
[[ -z "$UA" ]] && rotate_ua

#— Wordlist validation -------------------------------------------------------
[[ -f "$API_WL" ]] || API_WL="$COMMON"   # fallback if SecLists api/ absent
for wl in "$COMMON" "$WORDLIST" "$COMBINED"; do
    if [[ ! -f "$wl" ]]; then
        echo "[!] Wordlist not found: $wl"
        echo "    Check the path or use -w to override."
        exit 1
    fi
done

#— Global banner (per-target info prints inside run_target) ------------------
_tor_label="OFF — direct"
if $USE_TOR; then _tor_label="ON (torsocks)"; fi
_ck_label="none"
[[ -n "$COOKIE_STRING" ]] && _ck_label="set"

_canary_label="OFF"
if $USE_CANARY && $USE_TOR; then
    _canary_label="ON (retries=${TOR_MAX_RETRIES}, chunk=${TOR_MAX_REQ_PER_CIRCUIT})"
fi

if [[ "$HAS_AMASS"  = true ]]; then _amass_st="ON";  else _amass_st="OFF";  fi
if [[ "$HAS_KATANA" = true ]]; then _katana_st="ON"; else _katana_st="OFF"; fi
if [[ "$HAS_ARJUN"  = true ]]; then _arjun_st="ON";  else _arjun_st="OFF";  fi
if [[ "$HAS_KR"     = true ]]; then _kr_st="ON";     else _kr_st="OFF";     fi
if [[ "$HAS_NUCLEI" = true ]]; then _nuclei_st="ON"; else _nuclei_st="OFF"; fi

echo "[*] adv7FUZZ v${VERSION}"
if [[ ${#TARGET_LIST[@]} -gt 1 ]]; then
    echo "[*] Mode        : batch (${#TARGET_LIST[@]} targets from $TARGETS_FILE)"
else
    echo "[*] Mode        : single target"
fi
echo "[*] Scope codes : $MC"
echo "[*] Tor egress  : ${_tor_label}"
echo "[*] Canary/rotate: ${_canary_label}"
if $BURP_MODE; then
    echo "[*] Burp proxy  : ON (http://127.0.0.1:${BURP_PORT}) — torsocks disabled for ffuf"
    if $USE_TOR; then echo "[!] Tor+Burp    : Configure Burp upstream SOCKS → 127.0.0.1:9050 for anonymity"; fi
fi
echo "[*] Tools       : amass=${_amass_st}  katana=${_katana_st}  arjun=${_arjun_st}  kr=${_kr_st}  nuclei=${_nuclei_st}"
echo "[*] User-Agent  : ${UA:0:72}..."
echo "[*] Cookies     : ${_ck_label}"
_ac_label="ON"; if $NO_AC; then _ac_label="OFF (--no-ac)"; fi
_rr_label="OFF"; if $RECURSE_REDIRECTS; then _rr_label="ON (301/302/403 dirs in Phase 4)"; fi
echo "[*] ffuf -ac    : ${_ac_label}  |  recurse-redirects: ${_rr_label}"
echo ""

#— Placeholder globals (overwritten per-target by run_target) ----------------
TARGET=""
DOMAIN=""
DOMAIN_HOST=""
OUT=""
LOG=""

#— Base ffuf args (thread count set per-call) --------------------------------
# NOTE: -or omitted — ffuf v2.1.0-dev bug skips file creation even when
# matches exist. Empty-phase JSON files are handled safely in aggregation.
# -ac enables auto-calibration to filter uniform WAF/CDN responses.
# Disabled via --no-ac when app redirects all unauth requests uniformly (e.g. → /login).
BASE_FFUF=(
    -mc "$MC"
    -c
    -noninteractive
    -of json
)
if ! $NO_AC; then BASE_FFUF+=(-ac); fi
[[ -n "$COOKIE_STRING" ]] && BASE_FFUF+=(-b "$COOKIE_STRING")
[[ -n "$PROXY"         ]] && BASE_FFUF+=(-x "$PROXY")

#— Tor rotation helpers ------------------------------------------------------

# Return current Tor exit IP (empty on failure)
tor_get_exit_ip() {
    torsocks curl -s --max-time "$TOR_CANARY_TIMEOUT" \
        "https://check.torproject.org/api/ip" 2>/dev/null \
        | jq -r '.IP // empty' 2>/dev/null || true
}

# Return 0 (true) if target is returning a Cloudflare block signature:
#   HTTP 000 (timeout/refused) OR HTTP 403 with body in 4400–4700B range.
tor_is_blocked() {
    local _out _code _size
    _out=$(torsocks curl -s -o /dev/null -w "%{http_code} %{size_download}" \
        --max-time "$TOR_CANARY_TIMEOUT" -A "$UA" "$TARGET" 2>/dev/null) || _out="000 0"
    _code="${_out%% *}"
    _size="${_out##* }"
    [[ "$_code" == "000" ]] && return 0
    [[ "$_code" == "403" ]] && [[ "$_size" -ge 4400 ]] && [[ "$_size" -le 4700 ]] && return 0
    return 1
}

# Attempt Tor circuit rotation (two tiers). Returns 0 if new exit IP obtained.
tor_rotate() {
    local _attempt="${1:-1}"
    local _current_ip
    _current_ip=$(tor_get_exit_ip)
    echo "" | tee -a "$LOG"
    echo "[!] Tor exit blocked — rotating circuit (attempt ${_attempt}/${TOR_MAX_RETRIES})" \
        | tee -a "$LOG"
    echo "    Blocked exit : ${_current_ip:-unknown}" | tee -a "$LOG"

    # Tier 1: sudo systemctl restart tor (interactive — user enters password at terminal)
    echo "[*] Running: sudo systemctl restart tor" | tee -a "$LOG"
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
        echo "[!] Exit IP unchanged after restart — trying natural rotation" | tee -a "$LOG"
    else
        echo "[!] sudo restart failed. Tip: enable ControlPort for passwordless rotation:" \
            | tee -a "$LOG"
        echo "      /etc/tor/torrc → add: ControlPort 9051 + CookieAuthentication 1" \
            | tee -a "$LOG"
        echo "      then: sudo systemctl restart tor  (once to apply the config)" \
            | tee -a "$LOG"
    fi

    # Tier 2: wait 65s for natural Tor circuit expiry (~10 min rotation cycle)
    echo "[*] Waiting 65s for natural Tor circuit rotation..." | tee -a "$LOG"
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

# Canary check + retry loop. Call before each phase and between wordlist chunks.
# Returns 0 if circuit is clean (or canary/Tor disabled), 1 if max retries exceeded.
tor_check_and_rotate() {
    $USE_CANARY || return 0
    $USE_TOR    || return 0
    $DRY_RUN    && return 0   # no real requests in dry-run mode
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

#— Helper: run or dry-run ---------------------------------------------------
run_ffuf() {
    local phase_name="$1"
    local threads="$2"
    shift 2
    local -a cmd=(ffuf "${BASE_FFUF[@]}" -H "User-Agent: ${UA}" -t "$threads" "$@")
    if $USE_TOR && ! $BURP_MODE; then
        cmd=(torsocks "${cmd[@]}")
    fi
    echo "[*] Running ${phase_name}..." | tee -a "$LOG"
    local _cmd_log="${cmd[*]}"
    [[ -n "$COOKIE_STRING" ]] && _cmd_log="${_cmd_log//"$COOKIE_STRING"/***}"
    printf "    CMD: %s\n" "$_cmd_log" >> "$LOG"
    if $DRY_RUN; then
        echo "    [DRY-RUN] ${_cmd_log}"
        return 0
    fi
    "${cmd[@]}" 2>&1 | tee -a "$LOG"
}

#— Line count helper ---------------------------------------------------------
# awk NR correctly counts lines even when the file has no trailing newline.
# wc -l undercounts by 1 in that case, causing run_ffuf_chunked to exit its
# loop one iteration early and silently skip the last wordlist entry.
line_count() {
    local f="$1"
    if [[ -f "$f" ]]; then
        awk 'END { print NR }' "$f"
    else
        echo 0
    fi
}

#— Helper: chunked wordlist runner for long phases --------------------------
# Splits wordlist into TOR_MAX_REQ_PER_CIRCUIT-row chunks, runs a Tor canary
# between chunks, and merges the resulting JSON files into one output file.
run_ffuf_chunked() {
    local phase_name="$1" threads="$2" wl="$3" out_json="$4"
    shift 4
    local extra_args=("$@")
    local total_lines chunk_size chunk_num offset chunk_file chunk_out chunk_lines
    total_lines=$(line_count "$wl")
    chunk_size=$TOR_MAX_REQ_PER_CIRCUIT

    if [[ "$total_lines" -le "$chunk_size" ]]; then
        tor_check_and_rotate || true
        run_ffuf "$phase_name" "$threads" -w "$wl" -o "$out_json" "${extra_args[@]}"
        return
    fi

    echo "[*] ${phase_name} — ${total_lines} rows → chunks of ${chunk_size}" | tee -a "$LOG"
    chunk_num=0; offset=0
    local -a part_files=()

    while [[ "$offset" -lt "$total_lines" ]]; do
        chunk_file=$(mktemp "${TMPDIR:-/tmp}/adv7fuzz_chunk_XXXXXX")
        _CLEANUP_FILES+=("$chunk_file")
        tail -n +"$((offset + 1))" "$wl" | head -n "$chunk_size" > "$chunk_file"
        chunk_lines=$(line_count "$chunk_file")
        if [[ "$chunk_lines" -eq 0 ]]; then rm -f "$chunk_file"; break; fi

        chunk_out="${out_json%.json}_chunk${chunk_num}.json"
        part_files+=("$chunk_out")
        _CLEANUP_FILES+=("$chunk_out")

        tor_check_and_rotate || true
        run_ffuf "${phase_name} [chunk $((chunk_num + 1))]" "$threads" \
            -w "$chunk_file" -o "$chunk_out" "${extra_args[@]}"

        rm -f "$chunk_file"
        (( chunk_num++ )) || true
        (( offset += chunk_size )) || true
    done

    if [[ ${#part_files[@]} -gt 0 ]]; then
        jq -rs '{ results: [ .[].results[]? ] }' "${part_files[@]}" \
            > "$out_json" 2>/dev/null || true
        rm -f "${part_files[@]}"
        echo "[*] ${phase_name} — merged ${#part_files[@]} chunks → $(basename "$out_json")" \
            | tee -a "$LOG"
    fi
}

#— Helper: collect confirmed URLs from all phase JSON files ------------------
collect_endpoints() {
    local _ep_file="$OUT/all_endpoints.txt"
    local _tmp
    _tmp=$(mktemp "${TMPDIR:-/tmp}/adv7fuzz_endpoints_XXXXXX")
    _CLEANUP_FILES+=("$_tmp")
    # ffuf JSON phase results
    find "$OUT" -name 'phase*.json' | sort \
        | xargs -r jq -r '.results[]?.url // empty' 2>/dev/null \
        | grep -v '^$' >> "$_tmp" || true
    # katana crawl URLs (Phase 5 writes JSONL with .jsonl ext — extracted to .txt)
    [[ -f "$OUT/phase5_urls.txt" ]] && cat "$OUT/phase5_urls.txt" >> "$_tmp" || true
    sort -u "$_tmp" > "$_ep_file" 2>/dev/null || true
    rm -f "$_tmp"
    echo "[*] collect_endpoints: $(line_count "$_ep_file") unique → $_ep_file" \
        | tee -a "$LOG"
}

#— Phase 0: Subdomain enum (amass passive) -----------------------------------
run_phase0() {
    if ! $HAS_AMASS; then
        echo "[*] Phase 0 skipped — amass not installed" | tee -a "$LOG"
        return 0
    fi
    local _domain _out
    _domain="${TARGET#*//}"; _domain="${_domain%%/*}"; _domain="${_domain%%:*}"
    _out="${OUT}/phase0_subdomains.txt"
    local -a _cmd=(amass enum -passive -d "$_domain" -o "$_out")
    $USE_TOR && _cmd=(torsocks "${_cmd[@]}")
    tor_check_and_rotate || true
    echo "[*] Phase 0 — Subdomain Enum (amass passive)" | tee -a "$LOG"
    echo "    CMD: ${_cmd[*]}" | tee -a "$LOG"
    if $DRY_RUN; then echo "    [DRY-RUN] skipping execution"; return 0; fi
    "${_cmd[@]}" 2>&1 | tee -a "$LOG" || true
    echo "[*] Phase 0 complete — $(line_count "$_out") subdomains → $_out" \
        | tee -a "$LOG"
}

#— Phase 1: Fast recon (common.txt, no extensions) --------------------------
run_phase1() {
    tor_check_and_rotate || true
    run_ffuf "Phase 1 — Fast Recon" "$THREADS" \
        -u "${TARGET}/FUZZ" \
        -w "$COMMON" \
        -o "${OUT}/phase1_fast.json"
}

#— Phase 2: Extension scan (big.txt + extensions) ---------------------------
run_phase2() {
    run_ffuf_chunked "Phase 2 — Extension Scan" "$THREADS" \
        "$WORDLIST" "${OUT}/phase2_ext.json" \
        -u "${TARGET}/FUZZ" -e "$EXTS"
}

#— Phase 3: Combined wordlist + extensions -----------------------------------
run_phase3() {
    run_ffuf_chunked "Phase 3 — Combined Scan" "$THREADS" \
        "$COMBINED" "${OUT}/phase3_combined.json" \
        -u "${TARGET}/FUZZ" -e "$EXTS"
}

#— Phase 4: Recursive on dir-like 200s from Phase 1 -------------------------
run_phase4() {
    echo "[*] Running Phase 4 — Recursive..." | tee -a "$LOG"

    if [[ ! -f "${OUT}/phase1_fast.json" ]]; then
        echo "  [*] No Phase 1 output — skipping recursive scan." | tee -a "$LOG"
        return 0
    fi

    local -a phase4_dirs
    mapfile -t phase4_dirs < <(
        {
            # Always: directory-like 200s from Phase 1
            jq -r '.results[]? | select(.status==200 and (.url | test("\\.[a-z]{2,4}$") | not)) | .url' \
                "${OUT}/phase1_fast.json"
            # --recurse-redirects: also include 301/302/403 dirs (auth-protected trees)
            if $RECURSE_REDIRECTS; then
                jq -r '.results[]? | select((.status==301 or .status==302 or .status==403)
                    and (.url | test("\\.[a-z]{2,4}$") | not)) | .url' \
                    "${OUT}/phase1_fast.json"
            fi
        } | sort -u
    )

    if [[ ${#phase4_dirs[@]} -eq 0 ]]; then
        local _hint=""
        $RECURSE_REDIRECTS || _hint=" (try --recurse-redirects to also fuzz 301/302/403 dirs)"
        echo "  [*] No directory-like URLs in Phase 1 — skipping.${_hint}" | tee -a "$LOG"
        return 0
    fi

    local _p4_idx=0
    local _p4_base="${TARGET%%/}"
    for dir in "${phase4_dirs[@]}"; do
        if [[ "${dir#"$_p4_base"}" == "$dir" && "$dir" != "$_p4_base" ]]; then
            echo "  [!] Phase 4: off-target URL in phase1 output — skipping: $dir" | tee -a "$LOG"
            continue
        fi
        local _slug
        _slug="${dir##*/}"; _slug="${_slug//[^a-zA-Z0-9_-]/_}"; _slug="${_slug:-root}"
        echo "  [*] Recursive: $dir" | tee -a "$LOG"
        tor_check_and_rotate || true
        run_ffuf "Phase 4 — Recursive (${dir})" 30 \
            -u "${dir}/FUZZ" \
            -w "$COMMON" \
            -o "${OUT}/phase4_${_p4_idx}_${_slug}.json"
        (( _p4_idx++ )) || true
    done
}

#— Phase 5: Smart crawl (katana JS-aware spider) ----------------------------
run_phase5() {
    if ! $HAS_KATANA; then
        echo "[*] Phase 5 skipped — katana not installed" | tee -a "$LOG"
        return 0
    fi
    local _out_json="${OUT}/phase5_crawl.jsonl"
    local _out_urls="${OUT}/phase5_urls.txt"
    local -a _cmd=(katana -u "$TARGET" -jc -jsl -aff -d "$KATANA_DEPTH" \
        -H "User-Agent: ${UA}" -jsonl -o "$_out_json")
    $USE_TOR && _cmd=(torsocks "${_cmd[@]}")
    tor_check_and_rotate || true
    echo "[*] Phase 5 — Smart Crawl (katana depth=${KATANA_DEPTH})" | tee -a "$LOG"
    echo "    CMD: ${_cmd[*]}" | tee -a "$LOG"
    if $DRY_RUN; then echo "    [DRY-RUN] skipping execution"; return 0; fi
    "${_cmd[@]}" 2>&1 | tee -a "$LOG" || true
    jq -r 'try .request.endpoint // .url // empty' "$_out_json" 2>/dev/null \
        | sort -u > "$_out_urls" || true
    echo "[*] Phase 5 complete — $(line_count "$_out_urls") URLs → $_out_urls" \
        | tee -a "$LOG"
}

#— Phase 6: Parameter discovery (arjun) -------------------------------------
run_phase6() {
    if ! $HAS_ARJUN; then
        echo "[*] Phase 6 skipped — arjun not installed" | tee -a "$LOG"
        return 0
    fi
    collect_endpoints
    local _ep_file="$OUT/all_endpoints.txt"
    local _total
    _total=$(line_count "$_ep_file")
    if [[ "${_total:-0}" -eq 0 ]]; then
        echo "[*] Phase 6 — no endpoints collected; run Phase 1 first." | tee -a "$LOG"
        return 0
    fi
    local _out="${OUT}/phase6_params.json"
    local _targets_file
    _targets_file=$(mktemp "${TMPDIR:-/tmp}/adv7fuzz_arjun_targets.XXXXXX")
    _CLEANUP_FILES+=("$_targets_file")
    head -n "$ARJUN_MAX" "$_ep_file" > "$_targets_file"
    local -a _cmd=(arjun -i "$_targets_file" -oJ "$_out" -t 10 -q)
    $USE_TOR && _cmd=(torsocks "${_cmd[@]}")
    echo "[*] Phase 6 — Parameter Discovery (arjun, max=${ARJUN_MAX} endpoints)" | tee -a "$LOG"
    echo "    CMD: ${_cmd[*]}" | tee -a "$LOG"
    if $DRY_RUN; then rm -f "$_targets_file"; echo "    [DRY-RUN] skipping execution"; return 0; fi
    "${_cmd[@]}" 2>&1 | tee -a "$LOG" || true
    rm -f "$_targets_file"
    echo "[*] Phase 6 complete → $_out" | tee -a "$LOG"
}

#— Phase 7: API scanning (ffuf API wordlist + kiterunner) -------------------
run_phase7() {
    tor_check_and_rotate || true
    # 7a: ffuf against API-focused wordlist
    run_ffuf "Phase 7a — API Routes (ffuf)" "$THREADS" \
        -u "${TARGET}/FUZZ" -w "$API_WL" -o "${OUT}/phase7_api_ffuf.json"

    # 7b: kiterunner API brute-force
    if ! $HAS_KR; then
        echo "[*] Phase 7b skipped — kiterunner not installed" | tee -a "$LOG"
        return 0
    fi
    local _kr_out="${OUT}/phase7_api_kr.txt"
    local -a _cmd=(kiterunner scan "$TARGET" -w routes-large.kite \
        -H "User-Agent: ${UA}" --max-connection-timeout 10)
    $USE_TOR && _cmd=(torsocks "${_cmd[@]}")
    echo "[*] Phase 7b — API Routes (kiterunner)" | tee -a "$LOG"
    echo "    CMD: ${_cmd[*]}" | tee -a "$LOG"
    if $DRY_RUN; then echo "    [DRY-RUN] skipping execution"; return 0; fi
    "${_cmd[@]}" > "$_kr_out" 2>>"$LOG" || true
    echo "[*] Phase 7 complete — ffuf: ${OUT}/phase7_api_ffuf.json | kr: $_kr_out" | tee -a "$LOG"
}

#— Phase 8: Nuclei vulnerability scan ----------------------------------------
run_phase8() {
    if $NO_NUCLEI; then
        echo "[*] Phase 8 skipped — --no-nuclei flag set" | tee -a "$LOG"
        return 0
    fi
    if ! $HAS_NUCLEI; then
        echo "[*] Phase 8 skipped — nuclei not installed" | tee -a "$LOG"
        return 0
    fi
    collect_endpoints
    local _ep_file="$OUT/all_endpoints.txt"
    local _out="${OUT}/phase8_nuclei.json"
    local _total
    _total=$(line_count "$_ep_file")
    local _scan_flag _scan_target
    if [[ "${_total:-0}" -gt 0 ]]; then
        _scan_flag="-l"; _scan_target="$_ep_file"
    else
        _scan_flag="-u"; _scan_target="$TARGET"
    fi
    local -a _nuclei_oob=()
    [[ -n "$OOB_SERVER" ]] && _nuclei_oob=(-iserver "$OOB_SERVER")
    local -a _cmd=(nuclei "$_scan_flag" "$_scan_target" -tags "$NUCLEI_TAGS" \
        "${_nuclei_oob[@]}" \
        -H "User-Agent: ${UA}" -jle "$_out" -silent)
    $USE_TOR && _cmd=(torsocks "${_cmd[@]}")
    local _oob_note=""
    [[ -n "$OOB_SERVER" ]] && _oob_note=" (OOB: ${OOB_SERVER})"
    echo "[*] Phase 8 — Nuclei Scan (tags=${NUCLEI_TAGS}${_oob_note})" | tee -a "$LOG"
    echo "    CMD: ${_cmd[*]}" | tee -a "$LOG"
    if $DRY_RUN; then echo "    [DRY-RUN] skipping execution"; return 0; fi
    "${_cmd[@]}" 2>&1 | tee -a "$LOG" || true
    echo "[*] Phase 8 complete → $_out" | tee -a "$LOG"
}

#— Aggregate results for one target ------------------------------------------
aggregate_results() {
    echo "" | tee -a "$LOG"
    echo "[*] Aggregating results..." | tee -a "$LOG"

    shopt -s nullglob
    local -a _json_files=("${OUT}"/*.json)
    shopt -u nullglob

    if [[ ${#_json_files[@]} -eq 0 ]]; then
        echo "[!] No output files — no results for ${TARGET}" | tee -a "$LOG"
        return 0
    fi

    # 200/201/204 — direct hits
    jq -rs '[.[].results[]? | select(.status >= 200 and .status <= 204) | .url] | unique[]' \
        "${_json_files[@]}" > "${OUT}/all_200_urls.txt" 2>/dev/null || true

    # 301/302/307/308 — redirects with destination
    jq -rs '[.[].results[]?
        | select(.status >= 301 and .status <= 308)
        | "\(.url)\t->\t\(.redirectlocation // "?")\t[\(.status)]"
    ] | unique[]' \
        "${_json_files[@]}" > "${OUT}/all_redirects.txt" 2>/dev/null || true

    # 401/403/405 — auth walls and method restrictions
    jq -rs '[.[].results[]?
        | select(.status == 401 or .status == 403 or .status == 405)
        | "\(.url)\t[\(.status)]"
    ] | unique[]' \
        "${_json_files[@]}" > "${OUT}/all_auth_walls.txt" 2>/dev/null || true

    # Open redirect detection — redirect to a different host
    # Extract host[:port] from Location header, strip port, then check:
    # same domain OR subdomain of target → not an open redirect.
    jq -rs --arg host "$DOMAIN_HOST" \
        '[.[].results[]?
        | select(
            .status >= 301 and .status <= 308
            and ((.redirectlocation // "") | startswith("http"))
            and (
                ( (.redirectlocation // "")
                  | ltrimstr("https://") | ltrimstr("http://")
                  | split("/")[0] | split(":")[0]
                ) as $rhost
                | ($rhost == $host or ($rhost | endswith("." + $host))) | not
            )
        )
        | "OPEN-REDIRECT: \(.url) -> \(.redirectlocation) [\(.status)]"
    ] | unique[]' \
        "${_json_files[@]}" > "${OUT}/open_redirects.txt" 2>/dev/null || true

    local count_200 count_rdr count_auth count_open
    count_200=$(line_count "${OUT}/all_200_urls.txt")
    count_rdr=$(line_count "${OUT}/all_redirects.txt")
    count_auth=$(line_count "${OUT}/all_auth_walls.txt")
    count_open=$(line_count "${OUT}/open_redirects.txt")

    echo ""
    echo "────────────────────────────────────────────────────"
    echo "  adv7FUZZ v${VERSION}  |  ${TARGET}"
    echo "────────────────────────────────────────────────────"
    echo "  [+] 200/201/204 hits    : ${count_200}"
    echo "  [+] Redirects 3xx       : ${count_rdr}"
    echo "  [+] Auth walls 401-405  : ${count_auth}"
    echo "  [!] Open redirects      : ${count_open}"
    echo "────────────────────────────────────────────────────"
    echo "  Tor egress  : ${_tor_label}"
    echo "  User-Agent  : ${UA:0:60}..."
    echo "  Output dir  : $OUT"
    echo "  Full log    : $LOG"
    echo "────────────────────────────────────────────────────"

    [[ "$count_open" -gt 0 ]] && {
        echo ""
        echo "  [!] OPEN REDIRECTS DETECTED — review ${OUT}/open_redirects.txt"
        cat "${OUT}/open_redirects.txt"
    }
    [[ "$count_200" -gt 0 ]] && {
        echo ""
        echo "[+] Direct hits:"
        cat "${OUT}/all_200_urls.txt"
    }
    [[ "$count_rdr" -gt 0 ]] && {
        echo ""
        echo "[+] Redirects (original → destination [code]):"
        cat "${OUT}/all_redirects.txt"
    }
    [[ "$count_auth" -gt 0 ]] && {
        echo ""
        echo "[+] Auth walls / method restrictions:"
        cat "${OUT}/all_auth_walls.txt"
    }
}

#— Subdomain expansion: run Phases 1–8 on each Phase 0 subdomain ------------
run_subdomain_expansion() {
    local _scheme _parent_log _parent_out _sub_file _sub _sub_url _count=0 _sub_count
    _scheme="${TARGET%%://*}"
    _parent_log="$LOG"
    _parent_out="$OUT"
    _sub_file="${_parent_out}/phase0_subdomains.txt"

    if [[ ! -f "$_sub_file" ]]; then
        echo "[*] Phase 0 produced no subdomain file — expansion skipped." \
            | tee -a "$_parent_log"
        return 0
    fi
    _sub_count=$(line_count "$_sub_file")
    echo "[*] Subdomain expansion — ${_sub_count} subdomains to scan" \
        | tee -a "$_parent_log"

    while IFS= read -r _sub || [[ -n "$_sub" ]]; do
        [[ -z "$_sub" || "$_sub" =~ ^[[:space:]]*# ]] && continue
        _sub_url="${_scheme}://${_sub}"
        if ! [[ "$_sub_url" =~ ^https?://[^[:space:],]+$ ]]; then
            echo "[!] Skipping invalid subdomain: '$_sub'" | tee -a "$_parent_log"
            continue
        fi
        (( _count++ )) || true
        echo "[*] Subdomain [${_count}/${_sub_count}]: ${_sub_url}" \
            | tee -a "$_parent_log"
        run_target "$_sub_url" true
        LOG="$_parent_log"    # restore after run_target resets globals
        OUT="$_parent_out"
    done < "$_sub_file"

    echo "[*] Subdomain expansion complete — ${_count} scanned." \
        | tee -a "$_parent_log"
}

#— Per-target pipeline: reset globals, run phases, aggregate -----------------
run_target() {
    local _url="$1"
    local _is_sub="${2:-false}"

    # Reset per-target globals
    TARGET="$_url"
    local _d="${TARGET#*//}"; _d="${_d%%/*}"
    DOMAIN_HOST="${_d%%:*}"
    DOMAIN="${_d//[^a-zA-Z0-9._-]/_}"
    local _ts
    _ts=$(date +%Y%m%d_%H%M%S)
    OUT="./fuzz_${DOMAIN}_${_ts}"
    mkdir -p "$OUT" && chmod 700 "$OUT"
    LOG="${OUT}/adv7FUZZ_${_ts}.log"
    touch "$LOG" && chmod 600 "$LOG"
    rotate_ua

    echo "────────────────────────────────────────────────────"
    echo "[*] Target : $TARGET"
    echo "[*] Output : $OUT"
    echo ""

    if [[ -n "$ONLY_PHASE" ]]; then
        case "$ONLY_PHASE" in
            0) run_phase0 ;;
            1) run_phase1 ;;
            2) run_phase2 ;;
            3) run_phase3 ;;
            4) run_phase4 ;;
            5) run_phase5 ;;
            6) run_phase6 ;;
            7) run_phase7 ;;
            8) run_phase8 ;;
            *) echo "[!] Invalid phase '$ONLY_PHASE'. Use 0-8."; return 1 ;;
        esac
    else
        if ! $_is_sub; then
            $SKIP_PHASE0 || run_phase0
            if $SCAN_SUBDOMAINS && ! $SKIP_PHASE0; then
                run_subdomain_expansion
            fi
        fi
        run_phase1
        run_phase2
        run_phase3
        run_phase4
        run_phase5
        run_phase6
        run_phase7
        run_phase8
    fi

    aggregate_results
}

#— Main scan loop ------------------------------------------------------------
for _target_url in "${TARGET_LIST[@]}"; do
    run_target "$_target_url" false
done
