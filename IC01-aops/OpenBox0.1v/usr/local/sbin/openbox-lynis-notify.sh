#!/usr/bin/env bash
# openbox-lynis-notify.sh — extract lynis hardening index and send ntfy.
# [SEC-002] Replaces inline bash -c in ExecStartPost to avoid log-content injection.
set -euo pipefail
shopt -s inherit_errexit

idx=$(grep 'hardening_index' /var/log/lynis-report.dat 2>/dev/null | cut -d= -f2 || echo "?")
/usr/local/sbin/openbox-ntfy-send.sh "openbox-audit" "Lynis weekly: ${idx}"
