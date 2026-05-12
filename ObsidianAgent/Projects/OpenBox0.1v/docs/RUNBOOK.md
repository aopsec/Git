# OpenBox Runbook

## Healthchecks rápidos

```bash
# Status geral
systemctl status wg-quick@wg0 tor dnscrypt-proxy pihole-FTL nftables docker netdata

# IP egress (deve ser endpoint VPN)
curl -4 https://ifconfig.io

# Tor circuit OK
curl --socks5-hostname 127.0.0.1:9050 -s https://check.torproject.org/api/ip | jq .

# DNS leak
sudo /usr/local/sbin/openbox-dnsleak-check.sh

# Lynis quick
sudo lynis audit system --quick --no-colors | grep "Hardening index"
```

## Falhas comuns

### WireGuard handshake travado

```bash
sudo wg show wg0 latest-handshakes      # se > 180s
sudo systemctl restart wg-quick@wg0
journalctl -u wg-quick@wg0 -n 50
```

### Kill switch bloqueando handshake (boot)

Verificar ordem dos services:
```bash
systemctl list-dependencies wg-quick@wg0 | grep -E "nftables|network-online"
```
Garantir que `nftables.service` está listado em `After=` e que o endpoint VPN está na allowlist (`/usr/local/sbin/openbox-killswitch.sh`).

### Pi-hole respondendo, dnscrypt não

```bash
sudo systemctl status dnscrypt-proxy
ss -tlnp | grep 5053       # deve ter dnscrypt-proxy bound
sudo journalctl -u dnscrypt-proxy -n 30
```

### Pi-hole admin não abre via `/pihole`

```bash
ss -tlnp | grep 8081                     # upstream local esperado do admin Pi-hole
curl -kI https://openbox.lan/pihole/
sudo journalctl -u caddy -n 50
```

Se o upstream não existir, mova o admin web do Pi-hole para `127.0.0.1:8081` e recarregue o Caddy.

### Stremio container crash

```bash
docker logs stremio --tail 100
docker restart stremio
```

### Tor circuit unhealthy

```bash
sudo systemctl restart tor
sudo nyx       # interface curses
```

### Netdata painel não carrega via Caddy

```bash
sudo journalctl -u caddy -n 50
sudo tail -n 50 /var/log/caddy/openbox-access.log
curl -kI https://openbox.lan/netdata/
```

## Backup & restore

```bash
# Backup configs
sudo tar czf /mnt/backup/openbox-$(date +%F).tar.gz \
  /etc/wireguard /etc/tor /etc/dnscrypt-proxy /etc/nftables.conf \
  /etc/caddy /etc/fail2ban /etc/pihole /var/lib/aide/aide.db

# Restore
sudo tar xzf openbox-YYYY-MM-DD.tar.gz -C /
sudo systemctl daemon-reload
sudo systemctl restart wg-quick@wg0 tor dnscrypt-proxy pihole-FTL caddy nftables
```

## Atualização segura

```bash
sudo apt update
sudo apt list --upgradable
sudo apt full-upgrade -y
sudo systemctl daemon-reload
sudo /usr/local/sbin/openbox-killswitch.sh up   # re-aplica regras
sudo aide --check                                # detecta changes inesperadas
```

## Desligamento limpo

```bash
sudo systemctl stop wg-quick@wg0 tor dnscrypt-proxy pihole-FTL docker netdata
sudo systemctl poweroff
```
