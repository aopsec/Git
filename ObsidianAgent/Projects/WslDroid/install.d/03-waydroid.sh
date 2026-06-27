#!/usr/bin/env bash
# install.d/03-waydroid.sh — instalacao e inicializacao do Waydroid (Android 13 LXC)
set -euo pipefail
shopt -s inherit_errexit

# shellcheck source=_lib.sh
source "${WSLDROID_ROOT:?WSLDROID_ROOT nao definido}/install.d/_lib.sh"

readonly WAYDROID_KEYRING="/usr/share/keyrings/waydroid.gpg"
readonly WAYDROID_SOURCES="/etc/apt/sources.list.d/waydroid.list"
readonly WAYDROID_GPG_URL="https://repo.waydro.id/waydroid.gpg"
readonly WAYDROID_REPO_URL="https://repo.waydro.id/"
# O repo Waydroid publica apenas a suite 'jammy'; focal/noble fazem fallback para ela.
readonly WAYDROID_REPO_SUITE="jammy"

phase_header "03-waydroid: Instalacao e inicializacao do Waydroid"

# [FIX-WD03-GPG] O pipeline 'curl | gpg --dearmor | tee' do plano original quebra em
# DRY_RUN (o texto 'DRY: curl ...' viraria entrada do gpg) e mascara o exit code no tee.
# Encapsulamos o fluxo aqui: curto-circuito em dry-run e escrita atomica do keyring,
# preservando a intencao (chave assinada em keyring dedicado, sources com signed-by).
install_waydroid_keyring() {
  local tmp
  if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
    log INFO "DRY: baixa ${WAYDROID_GPG_URL} -> ${WAYDROID_KEYRING} (gpg --dearmor)"
    return 0
  fi
  tmp="$(mktemp)"
  # Falha em qualquer etapa (curl/gpg) aborta antes de instalar o keyring.
  if ! curl -fsSL "${WAYDROID_GPG_URL}" | gpg --dearmor > "${tmp}"; then
    rm -f "${tmp}"
    die "Falha ao baixar/desempacotar a chave GPG do Waydroid (${WAYDROID_GPG_URL})"
  fi
  run install -m 0644 "${tmp}" "${WAYDROID_KEYRING}"
  rm -f "${tmp}"
}

install_waydroid_sources() {
  local line="deb [signed-by=${WAYDROID_KEYRING}] ${WAYDROID_REPO_URL} ${WAYDROID_REPO_SUITE} main"
  if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
    log INFO "DRY: escreve ${WAYDROID_SOURCES} -> ${line}"
    return 0
  fi
  printf '%s\n' "${line}" | run_sh "tee '${WAYDROID_SOURCES}' > /dev/null"
  run chmod 0644 "${WAYDROID_SOURCES}"
}

install_waydroid() {
  local distro_codename
  # Codename detectado apenas para diagnostico; o repo so tem 'jammy'.
  distro_codename="$(lsb_release -sc 2>/dev/null || echo "${WAYDROID_REPO_SUITE}")"
  log INFO "Ubuntu detectado: ${distro_codename} (repo Waydroid usa suite '${WAYDROID_REPO_SUITE}')"

  install_waydroid_keyring
  install_waydroid_sources

  run apt-get update -qq
  run apt-get install -y waydroid
}

# --- Guards ---------------------------------------------------------------
detect_wsl2 || die "WSL2 necessario"
detect_binder || die "binder_linux ausente. Execute fase 02-kernel e reinicie o WSL2 antes."

# --- Skip se ja instalado e inicializado ----------------------------------
if command -v waydroid >/dev/null 2>&1 && [[ -f /var/lib/waydroid/INITIALIZED ]]; then
  log INFO "Waydroid ja instalado e inicializado. Pulando."
  log INFO "03-waydroid OK"
  exit 0
fi

# --- Instalacao (somente se ausente) --------------------------------------
if command -v waydroid >/dev/null 2>&1; then
  log INFO "Binario waydroid ja presente. Pulando instalacao do pacote."
else
  install_waydroid
fi

# --- Inicializacao com GAPPS ----------------------------------------------
log INFO "Inicializando Waydroid com GAPPS (Google Play Store)..."
warn "AVISO DE LICENCA: A build GAPPS contem software proprietario Google/Intel."
warn "Uso permitido apenas para fins nao-comerciais e pessoais."
run waydroid init -f -s GAPPS

# --- Servico systemd waydroid-container -----------------------------------
if command -v systemctl >/dev/null 2>&1; then
  run systemctl enable waydroid-container 2>/dev/null \
    || warn "systemctl enable falhou (normal em WSL2 sem systemd)"
  run systemctl start waydroid-container 2>/dev/null \
    || warn "systemctl start falhou — inicie manualmente: sudo systemctl start waydroid-container"
else
  warn "systemd nao detectado. Inicie o container manualmente: sudo waydroid container start"
fi

# --- Logs finais ----------------------------------------------------------
log INFO "03-waydroid OK"
log INFO "Para iniciar uma sessao: waydroid session start"
log INFO "Para abrir a interface: waydroid show-full-ui"
