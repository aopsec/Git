#!/usr/bin/env bash
#----------------------------------------------------------------------------
# Project	: adv7WebClone.sh
#----------------------------------------------------------------------------
# Date		: 20/05/2026
#----------------------------------------------------------------------------
# WheremI	: x
#----------------------------------------------------------------------------
# CreatedBy	: ADVAN7 Offensive Security | https://github.com/aopsec
#----------------------------------------------------------------------------

set -eo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

read -rp "Insert Target URL... ># " TARGET
[[ -z "$TARGET" ]] && { echo "[!] No URL provided. Aborting."; exit 1; }

# Derive site name and domain from URL for scoped crawl + dir layout
DOMAIN="${TARGET#*//}"
DOMAIN="${DOMAIN%%/*}"
SITENAME="${DOMAIN//[^a-zA-Z0-9._-]/_}"
LOGDIR="$HOME/websites/$SITENAME"
OUTDIR="$LOGDIR/clone"
LOGFILE="$LOGDIR/clone_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOGDIR"

# Guard destructive wipe of previous clone
if [[ -d "$OUTDIR" ]]; then
    read -rp "[!] $OUTDIR exists. Wipe and re-clone? [y/N] " CONFIRM
    [[ "${CONFIRM,,}" == "y" ]] || { echo "[*] Aborted."; exit 0; }
    rm -rf "$OUTDIR"
fi
mkdir -p "$OUTDIR"

# TLS pre-check — warn if cert invalid, do NOT skip silently
if ! curl -sSf --max-time 10 "$TARGET" -o /dev/null 2>/dev/null; then
    echo "[!] Warning: curl pre-check failed for $TARGET (bad cert or unreachable)."
    read -rp "    Proceed with --no-check-certificate? [y/N] " TLS_SKIP
    [[ "${TLS_SKIP,,}" == "y" ]] && TLS_FLAG="--no-check-certificate" || { echo "[*] Aborted."; exit 1; }
else
    TLS_FLAG=""
fi

echo "[*] Cloning $TARGET → $OUTDIR"
echo "[*] Log: $LOGFILE"

wget \
    --recursive \
    --level=inf \
    --convert-links \
    --adjust-extension \
    --page-requisites \
    --no-parent \
    --no-if-modified-since \
    --domains="$DOMAIN" \
    --user-agent="$UA" \
    --timeout=60 \
    --tries=3 \
    --wait=1 \
    --random-wait \
    --directory-prefix="$OUTDIR" \
    ${TLS_FLAG:+"$TLS_FLAG"} \
    "$TARGET" 2>&1 | tee "$LOGFILE"

echo "[+] Done. Files: $OUTDIR"
echo "[+] Log:   $LOGFILE"
