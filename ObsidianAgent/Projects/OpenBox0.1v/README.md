# OpenBox v0.2.0

Plataforma de borda Open Source com camadas honestas de privacidade, monitoramento e otimização — **retargeted (v0.2.0)** para placa generica Shenzhen **`R29_5G_LP3` (Rockchip RK3229, armhf, 1GB LPDDR3, 100Mbps Ethernet)** sobre **Armbian community `rk322x-box`** (Debian Bookworm).

> Sucessor técnico do projeto **TVBox OSS** (CEUB AV01, abr/2026), com correções factuais e arquitetura revisada após revisão técnica externa. v0.2.0 substitui o alvo Raspberry Pi 4 por hardware Shenzhen reaproveitado, com plano de mitigação de backdoors de cadeia de suprimento (BadBox 2.0 / Vo1d) documentado em `docs/security/RK3229_THREAT_RESEARCH.md`.

## Hardware fingerprint

Antes de instalar, capture o fingerprint da placa física:

```bash
sudo bash tools/fingerprint-rk3229.sh > docs/hw/r29_5g_lp3.txt 2>&1
```

Verifique manualmente as 4 portas do gate Phase 0 (SoC = rockchip,rk3229; arch = armhf; módulo wireguard presente; /dev/watchdog* existe). Sem isso, NÃO prossiga.

---

## O Que Mudou em Relação ao TVBox OSS

| Item | TVBox OSS | OpenBox v0.2.0 |
|---|---|---|
| Hardware alvo | RPi 4 4GB aarch64 (assumido) | **RK3229 R29_5G_LP3 1GB armhf** (real, Shenzhen reaproveitado) |
| Distro | Raspbian | **Armbian rk322x-box** community |
| Cripto VPN documentada | "AES-256" (errado) | **ChaCha20-Poly1305** (real) |
| Kill switch | snippet nftables sintaticamente quebrado | atomic ruleset + fwmark 51820 |
| DSCP marking | `ip mangle` (sintaxe iptables) | nftables `ip qos` chain |
| IRQ affinity | `cut -f1 -d:` frágil + `/etc/rc.local` | systemd unit + `awk` robusto |
| Stream via Tor | "sem impacto na experiência" (falso) | **Tor apenas metadados/DNS**, stream sob VPN |
| Servidor de mídia | Stremio (sem armhf) | **Jellyfin** (`jellyfin/jellyfin:latest` publica `linux/arm/v7`) |
| Install | `curl \| sudo bash` | download + sha256 verify + inspect + arch guard armhf |
| Auto-avaliação 5/5/5 | presente no entregue | removida |
| CAKE flow isolation | `diffserv4` only | `diffserv4` + `flows` (compat WireGuard) |
| Backdoor de cadeia | não discutido | **wipe + flash Armbian + verificação Vo1d** documentados |

---

## Arquitetura — 4 Camadas

```
+------------------------------------------------------------+
|  CAMADA 4 — AUDITORIA & MONITORAMENTO (off-path do stream) |
|  Netdata · Uptime Kuma · Monit · Lynis · RKHunter · ntfy   |
+------------------------------------------------------------+
|  CAMADA 3 — OTIMIZACAO KERNEL (zero-RAM, persistente)      |
|  TCP BBR · CAKE qdisc (flows) · IRQ affinity · MTU 1420    |
+------------------------------------------------------------+
|  CAMADA 2 — PRIVACIDADE (egress)                           |
|  RK3229 -> Pi-hole(53) -> dnscrypt(5053/DoH+DoQ) -> Internet|
|        \-> Tor(9050) ----- (apenas metadados/lookup) ----- |
|        \-> WireGuard(wg0) - (stream + traffic geral) ----- |
+------------------------------------------------------------+
|  CAMADA 1 — CORE MIDIA                                     |
|  Jellyfin Server (docker) :8096                            |
+------------------------------------------------------------+
```

**Egress real:** RK3229 → wg0 → ISP (toda mídia). Tor é túnel auxiliar para resolução/lookup de catálogos quando o addon suportar SOCKS5.

---

## Quick Start

```bash
git clone https://github.com/<voce>/openbox0.1v
cd openbox0.1v

# Inspecionar antes de executar
less install.sh
sha256sum install.sh
bash tests/ci-syntax-check.sh    # bash -n + shellcheck + nft check
python3 tools/sync_obsidian_vault.py --check
python3 tools/sync_obsidian_vault.py --sync

# v0.2.0 — Phase 0 hardware fingerprint (uma vez, na placa fisica RK3229)
sudo bash tools/fingerprint-rk3229.sh > docs/hw/r29_5g_lp3.txt 2>&1

# Instalacao real (requer root + arch armhf — install aborta caso contrario)
sudo ./install.sh --dry-run      # mostra o que seria feito
sudo ./install.sh                # instalacao completa
sudo ./install.sh --phase wireguard  # fase isolada
```

---

## Documentos

| Doc | Descrição |
|---|---|
| `docs/CASE_STUDY.md` | Estudo de caso completo (substitui o PDF original) |
| `docs/THREAT_MODEL.md` | Modelo de ameaça explícito + escopo |
| `docs/HARDENING_PLAN_v2.md` | Plano de implementação atualizado |
| `docs/RUNBOOK.md` | Procedimentos operacionais e troubleshooting |
| `docs/TOR_STREAMING_CAVEAT.md` | Por que stream via Tor não funciona |
| `docs/REFERENCES.md` | Bibliografia técnica com URLs ativos |
| `docs/OBSIDIAN_VAULT.md` | Como usar o projeto como vault do Obsidian |

## Obsidian Vault

O projeto agora pode ser aberto diretamente no Obsidian como vault local.

```bash
python3 tools/sync_obsidian_vault.py --check
python3 tools/sync_obsidian_vault.py --sync
bash tests/validate-obsidian-vault.sh
bash tests/phase-b-vault-tool.sh
```

Ponto de entrada no vault: `vault/Dashboards/OpenBox Vault Home.md`.
Sem flag, o CLI agora opera em modo conservador `--check` por padrão.

Contrato do vault gerado: `.aops-vault.toml`. O diretório universal padrão do Obsidian agent agora é `~/plugins/aops-agent/obsidian-agent/`.

Para uso repo-neutral fora do OpenBox:

```bash
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --init --repo /caminho/para/outro-repo
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --check --repo /caminho/para/outro-repo
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --sync --repo /caminho/para/outro-repo
```

## Validação

```bash
sudo ./tests/validate-stack.sh
# Testa: BBR ativo, CAKE ativo, WG handshake, IP egress = VPN,
#        DNS leak (so Pi-hole), Tor circuit (IsTor:true),
#        Lynis hardening index >= 75, kill switch (parar wg0 -> 0 vazamento)
```

## Status

**v0.2.0** — retargeted para RK3229 (R29_5G_LP3). Código + configs alinhados ao novo alvo; lint 74/0. Pendente: validação em placa física (Phase 0 fingerprint + Phase 1 boot baseline + smoke iperf3 sobre WireGuard). Use por sua conta e risco. Ver `docs/security/RK3229_THREAT_RESEARCH.md` antes de conectar a placa de fábrica a qualquer rede sem wipe.

## Licença

MIT — vide `LICENSE`.
