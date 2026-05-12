# Estudo de Caso — OpenBox v0.1

> Plataforma de Home Theater Open Source com Privacidade Auditável  
> Substituto técnico do projeto TVBox OSS (CEUB AV01, abril/2026)  
> Versão: 0.1 · Data: 2026-04-18

---

## Sumário Executivo

O **OpenBox v0.1** é uma reformulação honesta do projeto TVBox OSS após revisão técnica externa que identificou nove problemas críticos no documento original. Mantém-se o objetivo central — construir um dispositivo de home theater open source, auditável e econômico sobre Raspberry Pi 4 — mas corrige falhas factuais (algoritmo criptográfico, sintaxe de firewall), reformula o modelo de ameaça (escopo realista do que Tor pode/não pode fazer para streaming) e substitui artefatos placeholder por implementação rastreável.

**Investimento único:** R$ 805 · **Sem mensalidades** · **Auditoria contínua** via Netdata + Lynis + RKHunter + watchdogs custom.

---

## 1. Diagnóstico — O Problema Real

### 1.1 Contexto de Mercado (2026)

O ecossistema de streaming residencial em 2026 consolidou-se em três modelos:

| Modelo | Exemplos | Custo/mês | Privacidade |
|---|---|---|---|
| Hardware proprietário | Apple TV 4K, Chromecast com Google TV, Fire TV | R$ 0 (hw R$ 600+) | Telemetria ativa, ecossistema fechado |
| Smart TV integrada | LG webOS, Samsung Tizen | R$ 0 (embutido) | ACR (Automatic Content Recognition) ligado por padrão |
| Streaming subscription | Netflix, Disney+, Prime, Max, Globoplay | R$ 200-400 (4 serviços) | Coleta comportamental sistemática |

Dois problemas são ortogonais:

**Problema A — Privacidade:** Apple TV envia ~200 requests de telemetria/h em standby. Smart TVs com ACR enviam fingerprints de tudo que aparece na tela (incluindo conteúdo de HDMI externo) para servidores do fabricante. Vanderbilt + Princeton (2017, ainda relevante) documentaram a captura.

**Problema B — Custo composto:** Quatro assinaturas premium (R$ 200-400/mês) representam R$ 2.400-4.800/ano. Em 5 anos, R$ 12.000-24.000. Hardware open source com ROI de < 6 meses é matematicamente trivial.

### 1.2 A Lacuna Técnica

Não existe, em 2026, uma plataforma open source pronta-para-usar que combine:

1. Hardware acessível (< R$ 1.000 total)
2. SO completamente auditável (sem firmware proprietário no caminho de mídia)
3. Privacidade ativa (DNS encriptado, VPN com kill switch funcional, bloqueio de ACR)
4. Monitoramento integrado (não depender de telemetria externa para saber que o sistema está saudável)
5. Documentação técnica honesta (que não esconda limitações)

Soluções parciais existem — LibreELEC, OSMC, Pi-hole standalone, cada um cobrindo uma parte. **OpenBox endereça a integração**.

### 1.3 Lições do TVBox OSS (predecessor)

O documento original (TVBox OSS v2, abril/2026) acertou na **escolha de stack** — Raspberry Pi 4, WireGuard, Pi-hole, dnscrypt-proxy, Stremio, Netdata, CAKE qdisc são tecnologias maduras e adequadas. Mas falhou em:

| Categoria | Falha | Severidade |
|---|---|---|
| Factual | Documentou "AES-256" para WireGuard (correto: ChaCha20-Poly1305) | Crítica |
| Sintática | Kill switch nftables com regra incompleta (`ip daddr !=` sem valor) | Crítica |
| Sintática | DSCP marking usando `ip mangle` (sintaxe iptables, não nftables) | Alta |
| Arquitetural | Diagrama de fluxo invertido (egress como ingress) | Alta |
| Conceitual | Promessa "stream HD/4K via Tor sem impacto" — fisicamente impossível | Crítica |
| Operacional | Kill switch sem allowlist do endpoint → boot quebra após reboot | Alta |
| Procedimental | `curl \| sudo bash` num projeto que se vende como auditável | Alta |
| Editorial | URLs placeholder (`github.com/usuario/...`) na seção de evidências | Alta |
| Metodológica | Auto-avaliação 5/5/5 no documento entregue à banca | Média |

OpenBox v0.1 nasce dessa autocrítica.

---

## 2. Modelo de Ameaça (escopo explícito)

### 2.1 O Que OpenBox Protege Contra

| Ameaça | Camada | Mitigação |
|---|---|---|
| ISP observa quais serviços você acessa | L3 (rede) | WireGuard tunneling — ISP vê apenas o endpoint VPN |
| ISP/resolver observa quais domínios você resolve | L7 (DNS) | dnscrypt-proxy (DoH/DoQ + DNSSEC) → Pi-hole bloqueia trackers |
| Smart TV faz ACR no conteúdo | Hardware | OpenBox substitui a smart TV no caminho do conteúdo |
| Telemetria de SO/firmware proprietário | SW | Raspberry Pi OS Lite — sem firmware fechado no userspace de mídia |
| Brute-force em interfaces administrativas | App | Fail2ban + Caddy forward_auth + bind 127.0.0.1 |
| Comprometimento por update malicioso | Supply | install.sh com sha256 verify + `unattended-upgrades` security-only |
| Vazamento de tráfego se VPN cair | L3 | nftables kill switch atomic com fwmark 51820 |
| Tampering em binários do SO | FS | AIDE baseline + RKHunter daily |

### 2.2 O Que OpenBox **NÃO** Protege Contra

| Não-Ameaça Coberta | Por Quê | Mitigação Real |
|---|---|---|
| Anonimato perante adversário estatal | Tor sozinho não é anonimato; correlação de tráfego é viável | Tails + Tor Browser, off-OpenBox |
| Censura de conteúdo geo-bloqueado em CDN | VPN ajuda, mas CDNs detectam endpoints VPN | Mullvad/IVPN com IPs residenciais (custo extra) |
| Fingerprinting de browser dentro do Stremio | Aplicação não é hardened para isso | Use Tor Browser para conteúdo sensível, não Stremio |
| Logs do servidor VPN | Provedor pode logar | Escolha provedor com no-logs auditado (Mullvad, IVPN) |
| Comprometimento físico do dispositivo | Sem TPM, sem disk encryption por padrão | Adicione LUKS no SSD (fora do escopo v0.1) |

### 2.3 Honest Disclaimer — Tor para Streaming

**Streaming HD/4K via Tor não funciona e nunca vai funcionar.** A largura de banda média da rede Tor é 1-5 Mbps por circuito. Streaming 1080p exige ~8 Mbps; 4K HDR exige 25-50 Mbps. Exit nodes bloqueiam BitTorrent e UDP arbitrário. Latência adicional de 100-500ms quebra qualquer experiência interativa.

**O que OpenBox faz:** Tor é usado para resolução de DNS sensível e lookup de catalogos (quando o addon Stremio suporta SOCKS5 proxy). O **stream em si trafega via WireGuard direto**, sem Tor no caminho de dados.

Vide `docs/TOR_STREAMING_CAVEAT.md` para análise técnica completa.

---

## 3. Arquitetura Detalhada

### 3.1 Hardware (BOM verificada)

| Componente | Modelo | R$ |
|---|---|---|
| SBC | Raspberry Pi 4 Model B 4GB (Cortex-A72 1.8GHz) | 350 |
| Storage | SSD USB 3.0 64GB+ (Kingston A400 ou similar) | 120 |
| Bootloader | microSD 32GB Classe 10 (apenas firstboot) | 35 |
| PSU | Fonte oficial USB-C 5.1V/3A (não usar genérica) | 50 |
| Case | Argon ONE V2 (alumínio + fan ativo PWM) | 180 |
| Cabo vídeo | Micro-HDMI → HDMI 2.0 1m | 30 |
| Input | Mini teclado USB com touchpad ou Bluetooth + dongle | 40 |
| **Total** | | **805** |

### 3.2 Stack de Software

| Camada | Componente | Porta | RAM idle | Justificativa |
|---|---|---|---|---|
| SO | RPi OS Lite (Debian 12 Bookworm ARM64) | — | 180 MB | Headless, sem GUI desktop, kernel 6.x |
| Kernel tuning | sysctl (BBR, buffers) | — | 0 | Persistente via `/etc/sysctl.d/` |
| QoS | CAKE qdisc com flow isolation `flows` | — | 0 | **Compatível com WireGuard** (vide nota crítica) |
| Firewall | nftables atomic ruleset | — | 0 | Substitui iptables; `flush ruleset` no início |
| VPN | WireGuard (wg-quick@wg0) | UDP 51820 (out) | 8 MB | ChaCha20-Poly1305 + Curve25519 + opcional PSK |
| DNS encrypt | dnscrypt-proxy 2 | 127.0.0.1:5053 | 22 MB | DoH/DoT/DoQ + DNSSEC + anonymized relays |
| DNS filter | Pi-hole 6.x | 127.0.0.1:53 | 80 MB | Upstream = 127.0.0.1#5053 |
| Anonimização | Tor 0.4.x | 127.0.0.1:9050 (SOCKS5) | 50 MB | Apenas para metadados/lookup |
| Mídia | Stremio Server (container `tsaridas/stremio-docker`) | 8080, 11470, 12470 | 200 MB | ARM64 nativo, bundles player+server |
| Reverse proxy | Caddy 2.x | LAN 443 | 30 MB | TLS internal + forward_auth |
| Métricas | Netdata Agent v2 (tuned 10s/7d) | 127.0.0.1:19999 | 110 MB | Bind localhost; expor via Caddy |
| Uptime | Uptime Kuma v1.x (Docker) | 127.0.0.1:3001 | 65 MB | Monitora cada serviço da pilha |
| Admin | Cockpit (socket activation) | LAN 9090 | 2 MB idle | Só sobe quando acessado |
| Watchdog | Monit 5.x | 127.0.0.1:2812 | 10 MB | Auto-restart de serviços falhos |
| Notif. | ntfy self-hosted | 127.0.0.1:2586 | 15 MB | Push para celular via topic |
| IDS | Fail2ban + AIDE | — | 22 MB | Jails: SSH, Pi-hole admin, Caddy |
| Audit | Lynis (semanal) + RKHunter (diário) + chkrootkit | — | 0 (cron) | Baseline: hardening index ≥ 75 |
| Bandwidth | vnStat | — | 4 MB | Por interface (eth0 + wg0) |
| **Total persistente** | | | **~798 MB** | Sobra ~3.3 GB para buffer de stream |

### 3.3 Diagrama de Fluxo (egress correto)

```
[TV/HDMI] <-- [RPi 4 Stremio Container :8080]
                      |
                      v (HTTPS req para CDN/addon)
              [Pi-hole :53 (filtra)]
                      |
                      v
              [dnscrypt :5053 (encripta DNS)]
                      |
                      v
              [WireGuard wg0 (encapsula tudo)]
                      |
                      v ChaCha20-Poly1305 / UDP 51820
              [INTERNET / ISP ve apenas endpoint VPN]
                      |
                      v
              [VPN Provider Exit (Mullvad/IVPN)]
                      |
                      v
              [Destino: Stremio addon, CDN, etc]


Caminho auxiliar (apenas para addons configurados com SOCKS5):
[Stremio addon X] --SOCKS5--> [Tor :9050] --> [Tor circuit] --> [Destino]
                                       (latencia +500ms, OK para metadados)
```

### 3.4 Otimizações Kernel — Resumo Quantitativo

| Tuning | Camada OSI | Ganho medido (literatura) | Custo |
|---|---|---|---|
| TCP BBR | L4 | +14% throughput em links VPN/UDP-encapsulated | 0 RAM, sysctl |
| CAKE qdisc + flow `flows` | L2-L3 | Bufferbloat: ms→ms único dígito sob carga | 0 RAM, kernel built-in |
| WG MTU 1420 + MSS clamp | L3 | Elimina fragmentação intra-tunnel | 0 RAM, config |
| IRQ affinity (TX→CPU1, RX→CPU2) | Driver | RPi 4: ~540 → ~840 Mbps **raw** (não encriptado) | 0 RAM, awk script |
| sysctl rmem/wmem 16MB | L4 | Sustenta throughput em links de alta latência | 0 RAM |
| CPU governor performance | HW | Elimina latência de freq scaling | +0.5W consumo |

> **Nota honesta:** com WireGuard ativo (ChaCha20 em ARM Cortex-A72 sem aceleração HW), o throughput criptografado realista do RPi 4 é **350-500 Mbps**, não 936. Os 936 Mbps medidos pela TomCore referem-se a tráfego raw Ethernet, sem cripto. Stream 4K usa ~25-50 Mbps; folga continua confortável.

---

## 4. Implementação — Fases

| Fase | Descrição | Esforço | Artefato |
|---|---|---|---|
| 0 — Hardware | BOM, montagem, RPi imager, boot from SSD | 1h | manual |
| 1 — Base OS | apt update, SSH key-only, AIDE baseline, unattended-upgrades | 2h | `install.d/00-base.sh` |
| 2 — Kernel tuning | sysctl, CAKE, IRQ affinity, governor | 1h | `install.d/01-sysctl.sh` |
| 3 — Firewall | nftables atomic ruleset + kill switch | 2h | `install.d/02-nftables.sh` |
| 4 — VPN | WireGuard config + systemd ordering | 2h | `install.d/03-wireguard.sh` |
| 5 — DNS | dnscrypt-proxy → Pi-hole + leak test cron | 2h | `install.d/04-dns.sh` |
| 6 — Tor | torrc hardened + verificação cron | 1h | `install.d/05-tor.sh` |
| 7 — Mídia | Docker + Stremio container | 2h | `install.d/06-stremio.sh` |
| 8 — Monitoramento | Netdata + Uptime Kuma + Monit + ntfy + Fail2ban | 4h | `install.d/07-monitoring.sh` |
| 9 — Watchdogs | WG/Tor/DNS-leak watchdogs | 2h | `install.d/08-watchdogs.sh` |
| 10 — Validação | tests/validate-stack.sh + Lynis baseline | 2h | `install.d/09-validate.sh` |
| 11 — Docs | README, runbook, threat model | 4h | `docs/` |
| **Total** | | **~25h** | |

---

## 5. Trade-offs Explícitos

| Decisão | Trade-off |
|---|---|
| Tor apenas para metadados | Perde "anonimato pleno" (que era ilusório), ganha streaming funcional |
| Stremio em container | +overhead Docker (~50 MB), ganha portabilidade e isolamento |
| Caddy ao invés de Nginx | +30 MB RAM, ganha TLS automático e config simples |
| `flows` (não `triple-isolate`) | Perde fairness por host dentro do túnel, ganha funcionamento correto sob WG |
| RPi 4 (não 5) | -performance, +disponibilidade e custo menor abr/2026 |
| Caddy basic auth desabilitado | Perde simplicidade, evita CPU spike conhecido com Netdata (forward_auth) |
| Kill switch atomic vs PostUp inline | Perde acoplamento ao wg-quick, ganha persistência e atomicidade |

---

## 6. Métricas de Sucesso

Critérios objetivos auditáveis (script `tests/validate-stack.sh`):

| Métrica | Alvo | Comando |
|---|---|---|
| WG handshake recente | < 180s | `wg show wg0 latest-handshakes` |
| IP egress = endpoint VPN | true | `curl -4 https://ifconfig.io` |
| DNS leak | 0 servers fora do Pi-hole | `dnsleaktest.py` |
| Tor circuit OK | `IsTor: true` | `curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip` |
| BBR ativo | `bbr` | `sysctl net.ipv4.tcp_congestion_control` |
| CAKE ativo | qdisc cake presente | `tc -s qdisc show dev eth0` |
| Bufferbloat | grade A em waveform.com | manual |
| Lynis hardening index | ≥ 75 | `lynis audit system --quick` |
| Boot resilience | < 90s para stack pronta | `systemd-analyze` |
| Kill switch | tráfego = 0 com wg0 down | `systemctl stop wg-quick@wg0; curl --max-time 5 ifconfig.io` |

---

## 7. Comparativo OpenBox v0.1 vs Alternativas

| Característica | OpenBox v0.1 | Apple TV 4K | LibreELEC | OSMC | Stock Smart TV |
|---|---|---|---|---|---|
| Custo total inicial | R$ 805 | R$ 1.500 | R$ 600 | R$ 600 | R$ 0* |
| Mensalidade | R$ 0 | R$ 0 | R$ 0 | R$ 0 | R$ 0 |
| Open source | ✅ | ❌ | ✅ | ✅ | ❌ |
| Auditável (firmware) | ✅ | ❌ | parcial | parcial | ❌ |
| VPN integrada com kill switch | ✅ | ❌ | manual | manual | ❌ |
| DNS encriptado nativo | ✅ | ❌ | ❌ | ❌ | ❌ |
| Ad/tracker blocking sistêmico | ✅ Pi-hole | ❌ | ❌ | ❌ | ❌ |
| Telemetria do fabricante | ✅ zero | ❌ alta | ✅ zero | ✅ zero | ❌ alta (ACR) |
| Auditoria automatizada | ✅ Lynis/RKHunter | ❌ | ❌ | ❌ | ❌ |
| Painel de métricas | ✅ Netdata | ❌ | ❌ | ❌ | ❌ |
| Streaming HD/4K | ✅ via VPN | ✅ | ✅ | ✅ | ✅ |
| Setup técnico requerido | alto | nulo | médio | médio | nulo |
| Reproduzível em scripts | ✅ install.sh | ❌ | ✅ image | ✅ image | ❌ |

\* "R$ 0" da Smart TV é embutido no preço do TV.

---

## 8. Limitações Reconhecidas (v0.1)

1. **Não testado em hardware real** — esqueleto inicial; precisa shakedown de 7+ dias num RPi 4 físico.
2. **Sem CI** — `tests/ci-syntax-check.sh` cobre sintaxe (`bash -n`, `shellcheck`, `nft -c`), não comportamento.
3. **Sem disk encryption** — LUKS no SSD é opcional/manual; não automatizado.
4. **Sem 2FA nos paineis** — só basic auth/forward_auth via Caddy.
5. **IPv6 desabilitado** — simplifica VPN/Tor mas perde dual-stack; aceitar trade-off.
6. **Stremio container assume Docker disponível** — instalação dele está no install.d/06.
7. **Endpoint VPN hardcoded** — usuário precisa editar `etc/wireguard/wg0.conf.example` manualmente.

---

## 9. Roadmap

| Versão | Foco |
|---|---|
| **v0.1** | Esqueleto + correções factuais do TVBox OSS |
| v0.2 | Shakedown em hardware real; ajustes de RAM budget reais |
| v0.3 | LUKS opcional, 2FA paineis, Tor v3 hidden service para acesso remoto |
| v0.4 | Webhook integration (Discord/Telegram via ntfy) |
| v0.5 | Deploy multi-device (cluster RPi via Ansible) |
| v1.0 | CI green em RPi físico + relatório de hardening Lynis ≥ 85 |

---

## 10. Conclusão

OpenBox v0.1 não promete o que não pode entregar. Não há "anonimato total" via Tor, não há "stream 4K sem impacto" através de uma rede com gargalo de 5 Mbps, não há "auditabilidade" num projeto que se instala via `curl | sudo bash`. Cada camada tem escopo claro, custo conhecido e limitação reconhecida.

A diferença em relação ao TVBox OSS não é técnica — é editorial: o que mudou foi a postura de honestidade sobre o que o sistema realmente faz. As tecnologias escolhidas no projeto original eram corretas. As correções aqui são de fato-checking, sintaxe e arquitetura informacional.

**Quem deve usar OpenBox v0.1:**

- Estudantes de infraestrutura querendo um projeto real com stack moderna.
- Usuários técnicos cansados de ACR, telemetria de smart TV e custos crescentes de assinatura.
- Pesquisadores de privacidade procurando um lab reproduzível de DNS encriptado + VPN + audit.

**Quem NÃO deve usar:**

- Quem precisa de anonimato perante adversário estatal (use Tails).
- Quem espera plug-and-play (compre Apple TV).
- Quem quer streaming via Tor (não existe).

---

## Referências

Vide `docs/REFERENCES.md` para bibliografia técnica completa com URLs ativos verificados.

---

*Documento elaborado em 2026-04-18, sucessor crítico do TVBox OSS v2.*
