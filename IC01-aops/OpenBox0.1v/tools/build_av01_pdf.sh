#!/usr/bin/env bash
set -euo pipefail
shopt -s inherit_errexit

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_FILE="${ROOT_DIR}/deliverables/AV01_OpenBox_Audit_Report.ms"
OUT_FILE="${ROOT_DIR}/deliverables/AV01_OpenBox_Audit_Report.pdf"

tbl "${SRC_FILE}" | groff -ms -Tpdf > "${OUT_FILE}"
pdfinfo "${OUT_FILE}" >/dev/null

printf '%s\n' "${OUT_FILE}"
