#!/usr/bin/env bash
# Pipeline de build: AVAL01-IC.html → AVAL01-IC.pdf (Chromium) + .docx (Pandoc).
# Idempotente. Pandoc é opcional (DOCX é pulado se ausente, com aviso).

set -euo pipefail

cd "$(dirname "$0")"

SRC="AVAL01-IC.html"
PDF="AVAL01-IC.pdf"
DOCX="AVAL01-IC.docx"

if [[ ! -f "$SRC" ]]; then
  printf '[build] erro: %s não encontrado em %s\n' "$SRC" "$PWD" >&2
  exit 1
fi

printf '[build] fonte: %s\n' "$SRC"

# 1) Validação de sintaxe HTML (sanity check, não-bloqueante para deprecation).
if command -v xmllint >/dev/null 2>&1; then
  xmllint --noout --html "$SRC" 2>/tmp/aval01-xmllint.log || {
    printf '[build] aviso: xmllint reportou warnings (ver /tmp/aval01-xmllint.log)\n'
  }
fi

# 2) PDF via Chromium-compatible browser headless.
CHROME_CMD=""
for cmd in chromium chromium-browser google-chrome-stable google-chrome chrome msedge msedge.exe; do
  if command -v "$cmd" >/dev/null 2>&1; then
    CHROME_CMD="$cmd"
    break
  fi
done

find_windows_edge() {
  local dirs=(
    "/c/Program Files (x86)/Microsoft/Edge/Application"
    "/c/Program Files/Microsoft/Edge/Application"
    "/mnt/c/Program Files (x86)/Microsoft/Edge/Application"
    "/mnt/c/Program Files/Microsoft/Edge/Application"
  )
  for dir in "${dirs[@]}"; do
    if [[ -d "$dir" ]]; then
      local candidate
      candidate=$(find "$dir" -maxdepth 2 -type f -iname 'msedge.exe' 2>/dev/null | head -n 1 || true)
      if [[ -n "$candidate" ]]; then
        printf '%s' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

if [[ -z "$CHROME_CMD" && -x "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" ]]; then
  CHROME_CMD='/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
elif [[ -z "$CHROME_CMD" && -x "/c/Program Files/Microsoft/Edge/Application/msedge.exe" ]]; then
  CHROME_CMD='/c/Program Files/Microsoft/Edge/Application/msedge.exe'
elif [[ -z "$CHROME_CMD" && -x "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" ]]; then
  CHROME_CMD='/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
elif [[ -z "$CHROME_CMD" && -x "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe" ]]; then
  CHROME_CMD='/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe'
elif [[ -z "$CHROME_CMD" ]]; then
  if find_windows_edge >/dev/null 2>&1; then
    CHROME_CMD=$(find_windows_edge)
  fi
fi

if [[ -z "$CHROME_CMD" ]]; then
  printf '[build] erro: chromium ou navegador compatível não encontrado no PATH\n' >&2
  printf '[build]       instale chromium, microsoft edge ou adicione um link simbólico para chromium-browser\n' >&2
  exit 2
fi

USE_WINDOWS_BROWSER=false
if [[ "$CHROME_CMD" == *.exe ]] || [[ "$CHROME_CMD" == *msedge* ]]; then
  USE_WINDOWS_BROWSER=true
fi

if [[ "$USE_WINDOWS_BROWSER" == true ]]; then
  if command -v wslpath >/dev/null 2>&1; then
    WINDOWS_SRC=$(wslpath -w "$PWD/$SRC")
    WINDOWS_SRC=${WINDOWS_SRC//\\//}
    SRC_URI="file:///$WINDOWS_SRC"
    TMP_PDF=$(mktemp -u "/mnt/c/Users/AOPSec/AppData/Local/Temp/aval01-ic-XXXXXX.pdf")
    TMP_PDF_WIN=$(wslpath -w "$TMP_PDF")
    USER_DATA_DIR="/mnt/c/Users/AOPSec/AppData/Local/Temp/aval01-edge-profile"
    mkdir -p "$USER_DATA_DIR"
    USER_DATA_DIR_WIN=$(wslpath -w "$USER_DATA_DIR")
    OUT_PATH="$TMP_PDF_WIN"
  else
    SRC_URI="file://$PWD/$SRC"
    TMP_PDF=$(mktemp -u /tmp/aval01-ic-XXXXXX.pdf)
    OUT_PATH="$TMP_PDF"
    USER_DATA_DIR="/tmp/aval01-edge-profile"
  fi
else
  SRC_URI="file://$PWD/$SRC"
  TMP_PDF=$(mktemp -u /tmp/aval01-ic-XXXXXX.pdf)
  OUT_PATH="$TMP_PDF"
  USER_DATA_DIR="/tmp/aval01-edge-profile"
fi

rm -f "$PDF"
rm -f "$TMP_PDF"

printf '[build] gerando PDF temporário: %s\n' "$TMP_PDF"
printf '[build] usando navegador: %s\n' "$CHROME_CMD"
printf '[build] usando fonte URI: %s\n' "$SRC_URI"
printf '[build] usando usuário de dados: %s\n' "$USER_DATA_DIR"
printf '[build] usando saída para: %s\n' "$OUT_PATH"
"$CHROME_CMD" \
  --headless=new \
  --disable-gpu \
  --no-sandbox \
  --user-data-dir="$USER_DATA_DIR" \
  --no-pdf-header-footer \
  --virtual-time-budget=10000 \
  --print-to-pdf="$OUT_PATH" \
  "$SRC_URI" >/tmp/aval01-edge.log 2>&1

if [[ ! -s "$TMP_PDF" ]]; then
  printf '[build] erro: PDF temporário gerado vazio\n' >&2
  printf '[build] verifique /tmp/aval01-edge.log\n' >&2
  rm -f "$TMP_PDF"
  exit 3
fi

if ! head -c 4 "$TMP_PDF" | grep -q '%PDF'; then
  printf '[build] erro: PDF temporário inválido gerado\n' >&2
  printf '[build] verifique /tmp/aval01-edge.log\n' >&2
  rm -f "$TMP_PDF"
  exit 4
fi

mv "$TMP_PDF" "$PDF"

# 3) DOCX via Pandoc (opcional).
if command -v pandoc >/dev/null 2>&1; then
  printf '[build] gerando DOCX: %s\n' "$DOCX"
  pandoc "$SRC" \
    --from=html \
    --to=docx \
    --standalone \
    --metadata title="AVAL01 — Projeto Técnico (Introdução à Computação)" \
    -o "$DOCX"
else
  printf '[build] aviso: pandoc ausente — DOCX não gerado.\n'
  printf '[build]         instalar com: sudo pacman -S pandoc-cli\n'
fi

# 4) Hashes para rastreabilidade (alimentam §10 do documento).
printf '\n[build] artefatos gerados:\n'
ls -la "$SRC" "$PDF" 2>/dev/null
[[ -f "$DOCX" ]] && ls -la "$DOCX"

printf '\n[build] SHA-256:\n'
sha256sum "$SRC" "$PDF" 2>/dev/null
[[ -f "$DOCX" ]] && sha256sum "$DOCX"

printf '\n[build] ok.\n'
