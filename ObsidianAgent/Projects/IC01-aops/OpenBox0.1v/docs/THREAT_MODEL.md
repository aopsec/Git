# OpenBox — Threat Model v0.1

## Adversaries (in scope)

| Adversary | Capability | OpenBox mitigates? |
|---|---|---|
| ISP (passive) | observa metadata IP/SNI/DNS | ✅ WG + dnscrypt encripta tudo |
| ISP (active) | injeção/MITM, censura DNS | ✅ DNSSEC + DoH/DoQ via dnscrypt |
| LAN attacker | sniff de DNS, ataque Pi-hole admin | ✅ bind 127.0.0.1 + Caddy + Fail2ban |
| Smart TV ACR | fingerprint conteúdo | ✅ OpenBox substitui TV no caminho |
| Telemetria SO/firmware | callback proprietário | ✅ Debian + RPi OS Lite (audit) |
| Brute-force SSH público | dicionário/credenciais | ✅ key-only + Fail2ban + AllowUsers |
| Update malicioso (apt) | supply-chain | parcial — apt signing + unattended-upgrades security only |
| File integrity | tamper em binários | ✅ AIDE baseline + RKHunter |

## Out of scope (declare honestly)

- **State-level adversary** com capacidade de correlação de tráfego global → use Tails + Tor Browser, fora do OpenBox.
- **Adversary com acesso físico** ao RPi → sem TPM, sem LUKS automático em v0.1.
- **Compromisso do provedor VPN** → escolha provedor com no-logs auditado (Mullvad recomendado).
- **CDN/exit fingerprinting** → VPN endpoints conhecidos podem ser detectados; sem mitigação trivial.
- **Anonimato pleno via Tor** → não é o objetivo; Tor aqui é para metadados, não anonimato forense.

## Trust boundaries

```
[Untrusted Internet] | [VPN Provider] | [WG Tunnel] | [RPi local stack] | [LAN]
                     ^                  ^             ^                    ^
                     Trust = "no-logs"  Trust = math  Trust = audit       Trust = your wifi
```

## Failure modes & detection

| Failure | Detection | Action |
|---|---|---|
| WG tunnel down | watchdog (60s) | kill switch ativo + restart wg-quick |
| DNS leak (vazamento via fora do tunnel) | dnsleak cron diário | ntfy alert + log |
| Tor circuit broken | tor-check cron 30min | ntfy alert |
| Disk integrity alteration | AIDE diário | ntfy critical |
| Brute-force em paineis | Fail2ban | jail 10min, escala se reincidente |
| Service crash (Stremio/Pi-hole/Tor) | Monit | auto-restart + ntfy |
| RPi overheat | Netdata threshold 75°C | ntfy + log |
