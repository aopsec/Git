# Plano de Hardening v2 — OpenBox

> Versão revisada após pesquisa web (abr/2026). Substitui o plano original do TVBox OSS.

## Findings da Pesquisa Aplicados

### 1. WireGuard
- **PSK opcional** para resistência pós-quântica básica (combinado com ECDH no KDF). Pode ser distribuído via canal protegido por TLS 1.3 com ML-KEM hybrid (referência futura).
- **FwMark = 51820** habilitado para roteamento via fwmark e kill switch via nftables.
- **Nunca misturar UFW + nftables + iptables**. OpenBox usa nftables exclusivamente.

### 2. nftables (kill switch atomic)
- Arquivo iniciado com `#!/usr/sbin/nft -f` + `flush ruleset` para atomicidade.
- Preferir master config file (`/etc/nftables.conf`) ao invés de PostUp/PreDown inline.
- Allowlist explícita: loopback, oif wg0, endpoint VPN UDP/51820, LAN.

### 3. Tor torrc
- `SOCKSPort 0` se for usar Tor só para escutar — em OpenBox precisamos de SOCKS5 outbound, então mantemos `:9050`.
- `IsolateClientAddr,IsolateSOCKSAuth,IsolateClientProtocol,IsolateDestPort,IsolateDestAddr` — todos habilitados.
- `AvoidDiskWrites 1` (reduz wear no SSD).
- `DisableAllSwap 1` (lock memory pages).
- ExitPolicy customizada bloqueando ports sensíveis (já que não somos relay, só client outbound).

### 4. CAKE qdisc com WireGuard
- **CRÍTICO**: usar `flows` como flow isolation (NÃO `triple-isolate`/`hosts`/`srchost`/`dsthost`/`dual-srchost`/`dual-dsthost`). Os outros quebram o hash interno do túnel WG.
- Bandwidth: 85-95% do real ISP medido.
- Modo `diffserv4` para classificar voice/video/best-effort/bulk.

### 5. Pi-hole 6 + dnscrypt-proxy 2
- `systemctl edit dnscrypt-proxy.socket` para evitar conflito com FTLDNS.
- dnscrypt em `127.0.0.1:5053`, Pi-hole upstream `127.0.0.1#5053`.
- [FIX-AUDIT-PROXY] Admin web do Pi-hole em `127.0.0.1:8081`, com publicação externa somente via Caddy `/pihole`.
- Habilitar DoH3/DoQ (`http3 = true`).
- DNSSEC + `require_nolog` + `require_nofilter`.
- Anonymized DNS relays opcional (mais privacidade, +latência).

### 6. Netdata segurança
- Bind `127.0.0.1:19999`.
- Caddy reverse proxy com **`forward_auth`** (NÃO basic auth — issue conhecido de CPU spike com Netdata).
- Alternativa: bearer token (Netdata Cloud SSO se disponível).
- [FIX-AUDIT-F2B] Acesso via Caddy deve gerar access log dedicado para alimentar o jail `caddy-auth` do Fail2ban.

### 7. CIS Benchmark / Lynis
- Alvo: hardening index ≥ 75 (v0.1) → ≥ 85 (v1.0).
- Pacotes: `nftables`, `lynis`, `debsecan`, `apt-listchanges`, `unattended-upgrades`, `aide`, `rkhunter`, `chkrootkit`, `auditd`.
- Baseline AIDE pós-instalação completa.

### 8. Stremio ARM64
- Imagem oficial ARM64: `tsaridas/stremio-docker:latest` (suporta arm/v6, arm/v7, arm64/v8).
- Volume persistente `./stremio-data:/root/.stremio-server`.
- Variáveis: `NO_CORS=1`, `AUTO_SERVER_URL=1`.
- Porta 8080 (web player) + 11470/12470 (server interno).

## Ordem de Instalação Sequencial

```
00-base       → apt update, SSH hardening, AIDE init, unattended-upgrades
01-sysctl     → BBR, buffers, IPv4 hardening, kptr_restrict, IPv6 disable
02-nftables   → atomic ruleset com kill switch (drop policy + allowlist)
03-wireguard  → wg0 config + systemd ordering (After=nftables)
04-dns        → dnscrypt-proxy systemd override + Pi-hole + leak test
05-tor        → torrc hardened + verificação automatizada
06-stremio    → Docker engine + container tsaridas/stremio-docker
07-monitoring → Netdata + Uptime Kuma + Cockpit + Monit + ntfy + Caddy
08-watchdogs  → wg/tor/dns watchdogs como systemd timers
09-validate   → tests/validate-stack.sh + Lynis baseline + AIDE checkpoint
```

## Critérios de Aceite

- `bash tests/ci-syntax-check.sh` passa (bash -n + shellcheck + nft -c).
- `sudo tests/validate-stack.sh` passa todos os 10 checks.
- Lynis hardening index ≥ 75.
- Boot completo em < 90s (`systemd-analyze`).
- Kill switch: `systemctl stop wg-quick@wg0; curl --max-time 5 https://ifconfig.io` falha com timeout.
