# Changelog — OpenBox

## Unreleased

### Added
- **IPTV via Jellyfin Live TV** — `etc/openbox/iptv.conf` (fonte **iptv-org**, canais publicos legais/open-source), `usr/local/sbin/openbox-iptv-setup.sh` (registra tuner M3U + EPG XMLTV opcional via API do Jellyfin, idempotente; sem API key imprime os passos da UI), e hooks em `install.d/06-media.sh`: `OPENBOX_ENABLE_IPTV=1` configura o Live TV; `OPENBOX_JELLYFIN_LAN=1` publica o Jellyfin na LAN (`:8096`) sem Caddy.
- `etc/nftables/openbox-base.nft`: regra LAN opcional (comentada) para `tcp dport 8096`.

### Notes
- **Stremio continua indisponivel em ARMv7** (sem build) — IPTV usa Jellyfin, mantendo a decisao do retarget v0.2.0. Em 1GB sem HW transcode: apenas direct-play; usar subconjunto leve da iptv-org.
- `docs/RUNBOOK.md`: secao "Stremio container crash" substituida por "Jellyfin / IPTV Live TV".

## 0.2.0 — 2026-04-25 — RK3229 retarget

### Changed (hardware target)
- Plataforma de referencia: **Raspberry Pi 4 (4GB / aarch64) → Rockchip RK3229 (R29_5G_LP3 board, armhf, 1GB LPDDR3)**.
- Distro alvo: **Raspberry Pi OS Lite → Armbian community `rk322x-box`** (Debian Bookworm armhf, kernel >= 6.x com WireGuard in-tree).
- Stack drop: **Raspbian apt origin removida** de `install.d/00-base.sh` (Armbian publica sob `origin=Debian`).
- Arch guard adicionado em `install.sh`: install aborta se `dpkg --print-architecture != armhf`.

### Added
- `tools/fingerprint-rk3229.sh` — runner Phase 0 que captura 12 facts de hardware (SoC, kernel, RAM, eMMC, NIC, WireGuard, cpufreq, thermal, watchdog, Wi-Fi, crypto baseline) em `docs/hw/r29_5g_lp3.txt`.
- Helpers de runtime em `install.d/_lib.sh`: `detect_eth_iface`, `ram_kb`, `has_cpufreq`, `arch_is_armhf` (substituem hardcodes `eth0` / 4GB / aarch64).
- `docs/security/RK3229_THREAT_RESEARCH.md` — analise de ameacas pre-existentes (BadBox 2.0 / Vo1d / Triada / maskrom) e plano de mitigacao defensiva no fluxo flash-Armbian.

### Replaced
- **`install.d/06-stremio.sh` → `install.d/06-media.sh`** com Jellyfin (`jellyfin/jellyfin:latest` publica `linux/arm/v7`; Stremio nao). Porta 8080 -> 8096. Caddy front em `/jellyfin/*`. nftables DSCP rule ajustada.

### Tuned for 1GB RAM / 100Mbps NIC
- `etc/sysctl.d/99-openbox.conf`: TCP buffers 16MB -> 4MB max (rmem/wmem/tcp_rmem/tcp_wmem).
- `etc/monit/monitrc.d/openbox.conf`: alerta de memoria 85% -> 92%.
- `usr/local/sbin/openbox-tune.sh`: IFACE autodetect via default-route; BANDWIDTH 85mbit -> 95mbit; cpufreq guarded.
- `tests/validate-stack.sh`: CAKE check usa interface autodetectada; cpufreq governor check guarded; Lynis target 75 -> 70 (1st run).

## 0.1.0 — 2026-04-18

### Added
- Initial project skeleton derived from TVBox OSS academic project (CEUB AV01).
- Phased installer (`install.sh` + `install.d/`) with idempotent fases base/sysctl/nftables/wireguard/dns/tor/stremio/monitoring/watchdogs/validate.
- nftables atomic ruleset (`etc/nftables/openbox-base.nft`) with WireGuard kill switch via `fwmark 51820`.
- WireGuard config exemplo com PostUp/PostDown corretos e MTU 1420 + MSS clamp.
- dnscrypt-proxy 2 config com DoH/DoT/DoQ + DNSSEC + anonymized relays.
- Pi-hole upstream apontado para 127.0.0.1#5053 (sem conflito de socket).
- Tor torrc com `IsolateClientAddr/IsolateSOCKSAuth/IsolateClientProtocol/IsolateDestPort/IsolateDestAddr`, `AvoidDiskWrites 1`, `DisableAllSwap 1`, `SOCKSPort 0` para uso só como cliente outbound.
- CAKE qdisc com flow isolation `flows` (correto para WireGuard, não `triple-isolate`).
- Watchdogs: WireGuard handshake, Tor circuit health, DNS leak diário.
- Caddy reverse proxy com forward_auth (evitando overhead bcrypt do Netdata).
- Stremio via container `tsaridas/stremio-docker:latest` (ARM64 nativo).
- Threat model honesto: Tor para metadados/lookup, NÃO para stream HD/4K.

### Fixed (vs PDF original)
- "AES-256" → ChaCha20-Poly1305 (WireGuard) + AES-256-CTR ntor (Tor).
- Kill switch nftables com sintaxe quebrada (`oif != wg0 ip daddr != drop`) → atomic ruleset com fwmark routing.
- `ip mangle` (sintaxe iptables) → tabela nftables `ip qos` com chain `postrouting` priority `mangle`.
- IRQ affinity com `cut -f1 -d:` frágil → `awk` com `exit` no primeiro match.
- Boot race entre nftables.service e wg-quick@wg0 → systemd `After=`/`Wants=` explícitos.
- `curl | sudo bash` → download + sha256 verify + read antes de executar.
- Removida auto-avaliação 5/5/5 inadequada metodologicamente.
