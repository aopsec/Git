#!/usr/bin/env bash
#----------------------------------------------------------------------------
# Project     : adv7WebClone v0.0.3
# Description : Authorized offline site clone via recursive wget with Tor egress
# Date        : 21/05/2026
# CreatedBy   : ADVAN7 Offensive Security | https://github.com/aopsec
#----------------------------------------------------------------------------
# NOTE: wget fetches static HTML/CSS/JS assets. It cannot execute JavaScript,
#       so SPA frameworks (React, Angular, Vue) will be cloned as bare HTML.
#       For JS-rendered targets consider using katana or httrack instead.
#----------------------------------------------------------------------------
# USAGE:
#   ./adv7WebClone.sh -u <URL> [OPTIONS]
#   ./adv7WebClone.sh -L <file> [OPTIONS]
#   ./adv7WebClone.sh  (interactive prompt)
#
# OPTIONS:
#   -u URL       Target URL (e.g. https://target.com)
#   -L FILE      File of target URLs (one per line; # comments ignored)
#   -D FILE      File of extra domains/subdomains to include in --domains scope
#   -d DEPTH     Crawl depth (default: 5; use 0 for unlimited — be careful)
#   -w WAIT      Seconds between requests (default: 1, plus random jitter)
#   -x PROXY     HTTP/HTTPS proxy (e.g. http://127.0.0.1:8080 for Burp)
#   --no-tor     Skip torsocks, use direct egress (exposes real IP)
#   --ua STRING  Force a specific User-Agent string
#   --dry-run    Print the wget command without executing
#   -h|--help    Show this help
#----------------------------------------------------------------------------

set -uo pipefail   # no -e so TLS/wipe prompts can fail independently

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

#— Dependency check --------------------------------------------------------
for tool in wget torsocks curl; do
    if ! command -v "$tool" &>/dev/null; then
        echo "[!] Error: $tool not found. Install it first."
        exit 1
    fi
done

VERSION="0.0.3"

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

#— Defaults ----------------------------------------------------------------
TARGET=""
TARGET_FILE=""
DOMAINS_FILE=""
DEPTH=5
WAIT=1
USE_TOR=true
UA=""
PROXY=""
DRY_RUN=false

#— Argument parsing --------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -u)        [[ $# -gt 1 ]] || { echo "[!] -u requires an argument.";   exit 1; }; TARGET="$2";       shift 2 ;;
        -L)        [[ $# -gt 1 ]] || { echo "[!] -L requires an argument.";   exit 1; }; TARGET_FILE="$2";  shift 2 ;;
        -D)        [[ $# -gt 1 ]] || { echo "[!] -D requires an argument.";   exit 1; }; DOMAINS_FILE="$2"; shift 2 ;;
        -d)        [[ $# -gt 1 ]] || { echo "[!] -d requires an argument.";   exit 1; }; DEPTH="$2";        shift 2 ;;
        -w)        [[ $# -gt 1 ]] || { echo "[!] -w requires an argument.";   exit 1; }; WAIT="$2";         shift 2 ;;
        -x)        [[ $# -gt 1 ]] || { echo "[!] -x requires an argument.";   exit 1; }; PROXY="$2";        shift 2 ;;
        --no-tor)  USE_TOR=false; shift ;;
        --ua)      [[ $# -gt 1 ]] || { echo "[!] --ua requires an argument."; exit 1; }; UA="$2";           shift 2 ;;
        --dry-run) DRY_RUN=true;  shift ;;
        -h|--help)
            grep "^#" "$0" | grep -v "^#!/" | sed 's/^# \{0,\}//'
            exit 0 ;;
        *) echo "[!] Unknown option: $1"; exit 1 ;;
    esac
done

#— Validate numeric inputs -------------------------------------------------
if ! [[ "$DEPTH" =~ ^[0-9]+$ ]]; then
    echo "[!] -d DEPTH must be a non-negative integer (got: $DEPTH)."; exit 1
fi
if ! [[ "$WAIT" =~ ^[0-9]+$ ]]; then
    echo "[!] -w WAIT must be a non-negative integer (got: $WAIT)."; exit 1
fi

#— Validate file inputs ----------------------------------------------------
if [[ -n "$TARGET_FILE" && ! -f "$TARGET_FILE" ]]; then
    echo "[!] Target file not found: $TARGET_FILE"; exit 1
fi
if [[ -n "$DOMAINS_FILE" && ! -f "$DOMAINS_FILE" ]]; then
    echo "[!] Domains file not found: $DOMAINS_FILE"; exit 1
fi
if [[ -n "$TARGET" && -n "$TARGET_FILE" ]]; then
    echo "[!] -u and -L are mutually exclusive — pick one."; exit 1
fi

#— Build TARGETS array -----------------------------------------------------
TARGETS=()
if [[ -n "$TARGET_FILE" ]]; then
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        [[ "$_line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${_line// }"            ]] && continue
        if ! [[ "$_line" =~ ^https?://[^[:space:],]+$ ]]; then
            echo "[!] Skipping invalid URL in file: '$_line'"
            continue
        fi
        TARGETS+=("$_line")
    done < "$TARGET_FILE"
elif [[ -n "$TARGET" ]]; then
    if ! [[ "$TARGET" =~ ^https?://[^[:space:],]+$ ]]; then
        echo "[!] Invalid target URL: '$TARGET'"
        echo "    Must start with http:// or https:// and contain no spaces or commas."
        exit 1
    fi
    TARGETS=("$TARGET")
else
    read -rp "Insert Target URL... ># " TARGET
    [[ -z "$TARGET" ]] && { echo "[!] No URL provided. Aborting."; exit 1; }
    if ! [[ "$TARGET" =~ ^https?://[^[:space:],]+$ ]]; then
        echo "[!] Invalid target URL: '$TARGET'"
        echo "    Must start with http:// or https:// and contain no spaces or commas."
        exit 1
    fi
    TARGETS=("$TARGET")
fi
[[ ${#TARGETS[@]} -eq 0 ]] && { echo "[!] No valid targets found. Aborting."; exit 1; }

#— Tor pre-flight ----------------------------------------------------------
if $USE_TOR && ! ss -tlnp 2>/dev/null | grep -q "127.0.0.1:9050"; then
    echo "[!] Tor SOCKS not on 127.0.0.1:9050 — start Tor or pass --no-tor"
    exit 1
fi

#— Authorization gate — show all targets, ask once -------------------------
echo ""
echo "  [!] AUTHORIZATION REQUIRED"
printf "      Target%s:\n" "$( [[ ${#TARGETS[@]} -gt 1 ]] && echo 's' || true )"
for _t in "${TARGETS[@]}"; do echo "        - $_t"; done
echo "      You must have explicit written permission to clone ALL targets listed."
echo ""
read -rp "  Confirm you are authorized [yes/N] > " AUTH
[[ "${AUTH,,}" == "yes" ]] || { echo "[*] Aborted — authorization not confirmed."; exit 0; }
echo ""

#— Load EXTRA_DOMAINS from -D file -----------------------------------------
EXTRA_DOMAINS=()
if [[ -n "$DOMAINS_FILE" ]]; then
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        [[ "$_line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${_line// }"            ]] && continue
        EXTRA_DOMAINS+=("$_line")
    done < "$DOMAINS_FILE"
fi

#— Resolve UA once ---------------------------------------------------------
[[ -z "$UA" ]] && UA="${UA_LIST[$((RANDOM % ${#UA_LIST[@]}))]}"

#— clone_one() — core clone logic per target -------------------------------
clone_one() {
    local _target="$1"

    local _domain _host _sitename _logdir _outdir _logfile
    _domain="${_target#*//}"; _domain="${_domain%%/*}"
    _host="${_domain%%:*}"
    _sitename="${_domain//[^a-zA-Z0-9._-]/_}"
    _logdir="$HOME/websites/$_sitename"
    _outdir="$_logdir/clone"
    _logfile="$_logdir/clone_$(date +%Y%m%d_%H%M%S).log"

    mkdir -p "$_logdir"

    if [[ -d "$_outdir" ]]; then
        echo ""
        read -rp "  [!] $_outdir exists. Wipe and re-clone? [y/N] > " _confirm
        [[ "${_confirm,,}" == "y" ]] || { echo "[*] Skipping $_target."; return 0; }
        [[ "$_outdir" == "$HOME/websites/"* ]] || {
            echo "[!] Path sanity check failed: '$_outdir' outside \$HOME/websites/ — skipping."
            return 1
        }
        rm -rf "$_outdir"
    fi
    mkdir -p "$_outdir"

    #— TLS pre-check -------------------------------------------------------
    local _tls_flag=""
    local -a _curl_cmd
    if $USE_TOR; then
        _curl_cmd=(torsocks curl -sSf --max-time 15 "$_target" -o /dev/null)
    else
        _curl_cmd=(curl -sSf --max-time 10 "$_target" -o /dev/null)
    fi
    if ! "${_curl_cmd[@]}" 2>/dev/null; then
        echo "[!] Warning: TLS pre-check failed for $_target (bad cert or unreachable)."
        read -rp "    Proceed with --no-check-certificate? [y/N] > " _tls_skip
        [[ "${_tls_skip,,}" == "y" ]] && _tls_flag="--no-check-certificate" \
            || { echo "[*] Skipping $_target."; return 0; }
    fi

    #— Build --domains value -----------------------------------------------
    local _domains_arg="$_host"
    if [[ ${#EXTRA_DOMAINS[@]} -gt 0 ]]; then
        _domains_arg="${_host},$(IFS=,; echo "${EXTRA_DOMAINS[*]}")"
    fi

    #— Banner --------------------------------------------------------------
    echo "[*] adv7WebClone v${VERSION} — target: $_target"
    echo "[*] Depth       : $DEPTH"
    echo "[*] Wait        : ${WAIT}s (+ random jitter)"
    if $USE_TOR; then echo "[*] Tor egress  : ON (torsocks)"; else echo "[*] Tor egress  : OFF — direct"; fi
    [[ -n "$PROXY" ]] && echo "[*] Proxy       : $PROXY"
    echo "[*] Domains     : $_domains_arg"
    echo "[*] User-Agent  : ${UA:0:60}..."
    echo "[*] Output dir  : $_outdir"
    echo "[*] Log         : $_logfile"
    echo ""

    #— Tor + proxy chain warning -------------------------------------------
    if $USE_TOR && [[ -n "$PROXY" ]]; then
        echo "[!] Note: torsocks wraps wget's direct socket; proxy ($PROXY) connects"
        echo "    via localhost (bypassed by torsocks). For Burp→Tor chain, set Burp's"
        echo "    upstream SOCKS proxy to 127.0.0.1:9050 and use --no-tor here."
        echo ""
    fi

    #— Build wget command --------------------------------------------------
    local -a _cmd=(
        wget
        --recursive
        --level="$DEPTH"
        --convert-links
        --adjust-extension
        --page-requisites
        --no-parent
        --no-if-modified-since
        --domains="$_domains_arg"
        --user-agent="$UA"
        --timeout=60
        --tries=3
        --wait="$WAIT"
        --random-wait
        --directory-prefix="$_outdir"
    )
    [[ -n "$_tls_flag" ]] && _cmd+=("$_tls_flag")
    [[ -n "$PROXY"     ]] && _cmd+=(-e "http_proxy=$PROXY" -e "https_proxy=$PROXY")
    _cmd+=("$_target")
    $USE_TOR && _cmd=(torsocks "${_cmd[@]}")

    echo "[*] CMD: ${_cmd[*]}"
    echo ""
    if $DRY_RUN; then echo "    [DRY-RUN] skipping execution"; return 0; fi

    "${_cmd[@]}" 2>&1 | tee "$_logfile"
    local _exit=${PIPESTATUS[0]}

    echo ""
    if [[ $_exit -ne 0 ]]; then
        echo "[!] wget exited with code $_exit — log: $_logfile"
        return "$_exit"
    fi
    echo "[+] Done: $_target"
    echo "[+] Files : $_outdir"
    echo "[+] Log   : $_logfile"
}

#— Main loop ---------------------------------------------------------------
PASS=0
FAIL=0
for _url in "${TARGETS[@]}"; do
    if clone_one "$_url"; then
        (( PASS++ )) || true
    else
        (( FAIL++ )) || true
    fi
done

echo ""
echo "[+] Summary: ${PASS}/${#TARGETS[@]} target(s) cloned successfully."
[[ $FAIL -gt 0 ]] && echo "[!] $FAIL target(s) failed — check individual logs above."
[[ $FAIL -gt 0 ]] && exit 1 || exit 0
