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

# 2) PDF via Chromium headless.
if ! command -v chromium >/dev/null 2>&1; then
  printf '[build] erro: chromium não encontrado no PATH\n' >&2
  exit 2
fi

printf '[build] gerando PDF: %s\n' "$PDF"
chromium \
  --headless=new \
  --disable-gpu \
  --no-sandbox \
  --no-pdf-header-footer \
  --virtual-time-budget=10000 \
  --print-to-pdf="$PDF" \
  "file://$PWD/$SRC" >/dev/null 2>&1

if [[ ! -s "$PDF" ]]; then
  printf '[build] erro: PDF gerado vazio\n' >&2
  exit 3
fi

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
