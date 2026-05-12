# Referências Técnicas — OpenBox v0.1

URLs verificados em 2026-04-18.

## WireGuard
- Whitepaper original: https://www.wireguard.com/papers/wireguard.pdf
- Hardening Guide (Contabo): https://contabo.com/blog/hardening-your-wireguard-security-a-comprehensive-guide/
- Post-Quantum WireGuard Guide: https://engrxiv.org/preprint/view/5020
- WireGuard Performance Tuning: https://www.procustodibus.com/blog/2022/12/wireguard-performance-tuning/

## nftables / Kill switch
- Pro Custodibus — WireGuard com nftables: https://www.procustodibus.com/blog/2021/11/wireguard-nftables/
- xtarlit/wg-killswitch-nft (paranoid): https://github.com/xtarlit/wg-killswitch-nft
- xabadak/wg-lockdown: https://codeberg.org/xabadak/wg-lockdown
- Arch Wiki nftables: https://wiki.archlinux.org/title/Nftables

## Tor
- torrc(5) Debian: https://manpages.debian.org/testing/tor/torrc.5.en.html
- ArchWiki Tor: https://wiki.archlinux.org/title/Tor
- Tor stream isolation discussion: https://forum.torproject.org/t/tor-stream-isolation-using-torcc/3706
- Tor spec: https://spec.torproject.org/

## Pi-hole + DNS
- Pi-hole + dnscrypt-proxy guide: https://docs.pi-hole.net/guides/dns/dnscrypt-proxy/
- DNS Encryption 2026 (DoH/DoT/DoQ): https://packet.guru/blog/DNS-Encryption-in-2026
- Pi-hole 6 + DoH + Docker (2026): https://www.nodinrogers.com/post/2026-04-09-pihole-doh-docker/

## CAKE qdisc / Bufferbloat
- CAKE Recipes (bufferbloat.net): https://www.bufferbloat.net/projects/codel/wiki/CakeRecipes/
- CAKE com WireGuard (issue): https://github.com/dtaht/sch_cake/issues/141 (USE `flows` NOT `triple-isolate`)
- tc-cake notes: https://blog.lucid.net.au/2021/12/12/linux-tc-cake-notes/

## Stremio ARM64 Docker
- tsaridas/stremio-docker (arm64/v8): https://github.com/tsaridas/stremio-docker
- shivasiddharth/Stremio-RaspberryPi: https://github.com/shivasiddharth/Stremio-RaspberryPi

## Netdata + Caddy
- Netdata behind Caddy: https://learn.netdata.cloud/docs/netdata-agent/configuration/securing-agents/running-the-agent-behind-a-reverse-proxy/caddy
- Securing Netdata Agents: https://learn.netdata.cloud/docs/netdata-agent/configuration/securing-agents
- Caddy basic auth CPU issue (use forward_auth): https://github.com/caddyserver/caddy/issues/4267

## CIS Benchmark / Lynis
- CIS Benchmarks: https://www.cisecurity.org/cis-benchmarks
- Lynis: https://cisofy.com/lynis/
- Raspberry Pi CIS Hardening: https://github.com/nadin2025/raspberrypi-os-cis-hardening
- CIS Benchmark Audit Ubuntu 2026: https://oneuptime.com/blog/post/2026-03-02-how-to-run-cis-benchmark-audits-on-ubuntu/view

## Linux Hardening 2026
- Linux Security Hardening Guide 2026: https://dgmicro.com/linux-security-hardening-guide-2026-essential-commands-and-best-practices-for-sy
- Privacy Hardening Guide 2026: https://discuss.tchncs.de/post/56831968

## Hardware
- Raspberry Pi 4 Model B: https://www.raspberrypi.com/products/raspberry-pi-4-model-b/
- TomCore RPi 4B Network Performance: https://tomcore.io/docs/articles/RaspberryPI/raspberry-pi-4b-network-performance/
