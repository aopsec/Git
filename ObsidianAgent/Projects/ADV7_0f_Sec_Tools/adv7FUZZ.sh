#!/usr/bin/env bash
#----------------------------------------------------------------------------
# Project	: adv7FUZZ
#----------------------------------------------------------------------------
# Date		: 20/05/2026
#----------------------------------------------------------------------------
# WheremI	: x
#----------------------------------------------------------------------------
# CreatedBy	: ADVAN7 Offensive Security | https://github.com/aopsec
#----------------------------------------------------------------------------

set -uo pipefail   # no -e so phases can fail independently

# Dependency check
for tool in ffuf jq; do
    if ! command -v "$tool" &>/dev/null; then
        echo "[!] Error: $tool not found. Install it first."
        exit 1
    fi
done

# Read target URL from user
read -rp "Insert Target URL... ># " TARGET

WORDLIST="/home/aops/OPia/Git/wordlists/SecLists/SecLists/Discovery/Web-Content/big.txt"
COMMON="/home/aops/OPia/Git/wordlists/SecLists/Discovery/Web-Content/common.txt"
COMBINED="/home/aops/OPia/Git/wordlists/SecLists/Discovery/Web-Content/combined_words.txt"
OUT="./scan_$(date +%Y%m%d_%H%M)"
mkdir -p "$OUT"

# Phase 1: Fast 200 recon (common.txt, no extensions)
echo "[*] Running Phase 1..."
ffuf -u "${TARGET}/FUZZ" -w "$COMMON" \
    -mc 200 -t 50 -c -noninteractive \
    -o "${OUT}/phase1_fast.json" -of json

if [ ! -f "${OUT}/phase1_fast.json" ]; then
    echo "[!] ERROR: FUZZ PHASE 1 FAILED"
    exit 1
fi

# Phase 2: Medium wordlist + extensions
echo "[*] Running Phase 2..."
ffuf -u "${TARGET}/FUZZ" -w "$WORDLIST" \
    -e .php,.html,.txt,.bak,.zip,.sql,.conf,.old,.jar \
    -mc 200 -t 40 -c -noninteractive \
    -o "${OUT}/phase2_ext.json" -of json

# Phase 3: Combined wordlist + extensions
echo "[*] Running Phase 3..."
ffuf -u "${TARGET}/FUZZ" -w "$COMBINED" \
    -e .php,.html,.txt,.bak,.zip,.sql,.conf,.old,.jar \
    -mc 200 -t 50 -c -noninteractive \
    -o "${OUT}/phase3_Combined.json" -of json

# Phase 4: Recursive on discovered dirs (dirs only = no file extension in URL)
# FIX: mapfile+for avoids ffuf consuming stdin from the jq pipe (caused hang).
# FIX: removed 2>/dev/null so ffuf errors surface; -noninteractive replaces it.
# FIX: explicit empty-array guard prints diagnostic instead of silent skip.
echo "[*] Running Phase 4 (Recursive)..."
mapfile -t phase4_dirs < <(
    jq -r '.results[] | select(.status==200 and (.url | test("\\.[a-z]{2,4}$") | not)) | .url' \
        "${OUT}/phase1_fast.json"
)
if [ ${#phase4_dirs[@]} -eq 0 ]; then
    echo "  [*] No directory-like URLs found in Phase 1 — skipping recursive scan."
else
    for dir in "${phase4_dirs[@]}"; do
        echo "  [*] Scanning: $dir"
        ffuf -u "${dir}/FUZZ" -w "$COMMON" \
            -mc 200 -t 30 -c -noninteractive \
            -o "${OUT}/phase4_$(basename "${dir}").json" -of json
    done
fi

# Aggregate all 200 URLs
echo "[*] Aggregating results..."
shopt -s nullglob
json_files=("${OUT}"/*.json)
if [ ${#json_files[@]} -eq 0 ]; then
    echo "[!] No output files to aggregate."
    exit 0
fi
jq -rs '[.[].results[]? | select(.status==200) | .url] | unique[]' \
    "${json_files[@]}" > "${OUT}/all_200_urls.txt"
echo "[+] Unique 200 URLs found: $(wc -l < "${OUT}/all_200_urls.txt")"
cat "${OUT}/all_200_urls.txt"
