#!/usr/bin/env bash
# usr/local/sbin/openbox-iptv-setup.sh — registra fonte IPTV (iptv-org) no Jellyfin Live TV.
# OpenBox v0.2.0 (RK3229 / armhf). Idempotente. Fonte: APENAS iptv-org (legal/open-source).
#
# Uso:
#   sudo openbox-iptv-setup.sh                      # usa /etc/openbox/iptv.conf
#   JELLYFIN_API_KEY=xxxxx sudo openbox-iptv-setup.sh
#
# Sem API key  -> imprime os passos da UI do Jellyfin (Dashboard -> Live TV) e sai 0
#                 (nao falha o install; nao cria admin automaticamente).
# Com API key  -> registra M3U TunerHost (+ EPG XMLTV opcional) e atualiza o guia.
#                 API key: env JELLYFIN_API_KEY ou arquivo /etc/openbox/jellyfin-api.key.
set -euo pipefail

CONF="${OPENBOX_IPTV_CONF:-/etc/openbox/iptv.conf}"
API_KEY_FILE="/etc/openbox/jellyfin-api.key"

log() { printf '[iptv-setup] %s\n' "$*"; }
err() { printf '[iptv-setup] ERRO: %s\n' "$*" >&2; exit 1; }

[[ -r "$CONF" ]] || err "config ausente ou ilegivel: $CONF"
# shellcheck source=/dev/null
. "$CONF"
: "${IPTV_M3U_URL:?IPTV_M3U_URL nao definido em $CONF}"
: "${JELLYFIN_URL:=http://127.0.0.1:8096}"
: "${IPTV_TUNER_NAME:=OpenBox IPTV (iptv-org)}"
IPTV_EPG_URL="${IPTV_EPG_URL:-}"

# API key: env tem prioridade sobre o arquivo
API_KEY="${JELLYFIN_API_KEY:-}"
if [[ -z "$API_KEY" && -r "$API_KEY_FILE" ]]; then
  API_KEY="$(tr -d ' \r\n' < "$API_KEY_FILE")"
fi

# Espera o Jellyfin responder (ate ~60s)
log "aguardando Jellyfin em ${JELLYFIN_URL} ..."
ready=0
i=0
while [[ "$i" -lt 30 ]]; do
  if curl -fsS -m 5 "${JELLYFIN_URL}/health" >/dev/null 2>&1; then ready=1; break; fi
  i=$((i + 1))
  sleep 2
done
[[ "$ready" -eq 1 ]] || err "Jellyfin nao respondeu em ${JELLYFIN_URL}/health"
log "Jellyfin OK."

print_ui_steps() {
  cat <<EOF
[iptv-setup] Sem JELLYFIN_API_KEY — configure pela UI do Jellyfin (~2 min):
  1) Abra o Jellyfin e finalize o primeiro acesso (crie o usuario admin).
  2) Dashboard -> Live TV -> Tuner Devices -> (+)
       Tuner Type:   M3U Tuner
       File or URL:  ${IPTV_M3U_URL}
  3) (opcional) TV Guide Data Providers -> (+) -> XMLTV
       File or URL:  ${IPTV_EPG_URL:-<sem EPG configurado>}
  4) Salve, aguarde o guia carregar e abra "Live TV".
  Para automatizar: Dashboard -> API Keys -> gere uma key, grave em
  ${API_KEY_FILE} (chmod 600) e rode este script novamente.
EOF
}

if [[ -z "$API_KEY" ]]; then
  log "nenhuma API key (env JELLYFIN_API_KEY ou ${API_KEY_FILE})."
  print_ui_steps
  exit 0
fi

hdr=(-H "X-Emby-Token: ${API_KEY}" -H "Content-Type: application/json")

# Idempotencia: tuner M3U com esta URL ja existe?
existing="$(curl -fsS "${hdr[@]}" "${JELLYFIN_URL}/LiveTv/TunerHosts" 2>/dev/null || true)"
if printf '%s' "$existing" | grep -qF "$IPTV_M3U_URL"; then
  log "tuner M3U ja registrado para ${IPTV_M3U_URL} — nada a fazer."
else
  log "registrando tuner M3U: ${IPTV_M3U_URL}"
  curl -fsS -X POST "${hdr[@]}" "${JELLYFIN_URL}/LiveTv/TunerHosts" \
    -d "{\"Type\":\"m3u\",\"Url\":\"${IPTV_M3U_URL}\",\"FriendlyName\":\"${IPTV_TUNER_NAME}\",\"AllowHWTranscoding\":false,\"ImportFavoritesOnly\":false}" \
    >/dev/null || err "falha ao registrar tuner M3U (o schema da API pode variar por versao — use a UI: Dashboard -> Live TV)"
  log "tuner M3U registrado."
fi

# EPG XMLTV (opcional)
if [[ -n "$IPTV_EPG_URL" ]]; then
  log "registrando EPG XMLTV: ${IPTV_EPG_URL}"
  curl -fsS -X POST "${hdr[@]}" "${JELLYFIN_URL}/LiveTv/ListingProviders?validateListings=false" \
    -d "{\"Type\":\"xmltv\",\"Path\":\"${IPTV_EPG_URL}\"}" \
    >/dev/null || log "AVISO: falha ao registrar EPG (opcional). Configure pela UI se quiser guia."
fi

# Atualiza o guia (best-effort)
log "disparando refresh do guia..."
curl -fsS -X POST "${hdr[@]}" "${JELLYFIN_URL}/LiveTv/GuideRefresh" >/dev/null 2>&1 || true

# Conta canais carregados
channels="$(curl -fsS "${hdr[@]}" "${JELLYFIN_URL}/LiveTv/Channels?Limit=0" 2>/dev/null \
  | grep -oE '"TotalRecordCount":[0-9]+' | head -1 | grep -oE '[0-9]+' || true)"
log "OK — canais Live TV detectados: ${channels:-?}"
