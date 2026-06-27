#!/usr/bin/env bash
# waydroid-adb.sh — Ambiente ADB e display para WslDroid/Waydroid
# Template: instalado em /etc/profile.d/ pelo WslDroid install.sh
# NAO editar no sistema — edite o template no repositorio

# Display (WSLg)
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export DISPLAY="${DISPLAY:-:0}"

# IP do host Windows
export WIN_IP
WIN_IP="$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf 2>/dev/null || echo '127.0.0.1')"

# Para usar o servidor ADB do host Windows (dispositivos USB via usbipd-win):
#   export ADB_SERVER_SOCKET="tcp:${WIN_IP}:5037"
# Para Waydroid (padrao):
#   adb connect localhost:5555
