# Guia de Setup & Boot — R3290_V8.1 (Rockchip Genérico)

> **Procedimento Universal para TV Box Rockchip R3290 / Variantes**  
> Formatação de hardware Android pré-infectado para Armbian limpo  
> Versão: 1.0 (Adaptável) · Data: 2026-04-25

---

## § 1. Introdução & Status de Documentação

### Aviso Importante: Dispositivo Pouco Documentado

O **R3290_V8.1** é uma variante de TV box Rockchip que **não possui documentação pública consolidada**. Este guia foi criado como **framework adaptável** baseado em:

1. Padrões Rockchip documentados (RK3229, RK3288, RK3328)
2. Procedimentos universais de maskrom + rkdeveloptool
3. Estrutura paralela ao guia RK3229 existente
4. Pressupostos sobre "V8.1" sendo uma PCB revision posterior

### O que você PRECISA fazer primeiro

Antes de começar qualquer procedimento:

**PASSO 0 — Identificar o SoC Exato**

```bash
# Opção 1: Abrir o dispositivo e ler PCB silkscreen
# Procure por: "RK3289", "RK3288", "RK3228A", "RK3328", "RK3390" impresso no PCB
# Anote EXATAMENTE o número do SoC (exemplo: "RK3328_V1.2")

# Opção 2: Se Armbian já está rodando:
cat /proc/device-tree/model
# Output esperado: "rockchip,rk3288-..." ou "rockchip,rk3328-..." ou similar

# Opção 3: Via serial console durante boot (ver § Apêndice A)
# Kernel log mostrará: "Rockchip RK3288 ..." ou "RK3328 ..."

# Opção 4: Pesquisa comunitária
# Buscar no GitHub/XDA/Armbian: "R3290_V8.1" + "rockchip"
# ou trazer imagens PCB para análise
```

**Por que isso importa**: O procedimento de maskrom é idêntico entre SoCs Rockchip, MAS a imagem Armbian correta varia. Se você flashar a imagem errada, o device não bootará.

---

## § 2. Identificação de Hardware — R3290_V8.1

### Especificações Esperadas (Baseadas em Padrão Rockchip)

| Componente | R3290_V8.1 (Esperado) | Variação Possível |
|-----------|----------------------|-------------------|
| **SoC** | Rockchip (RK3288, RK3328, ou RK3329 provável) | RK3289, RK3390 improvável |
| **CPU** | Quad-core ARM Cortex-A7 ou A17 @ 1.4–2.0 GHz | Frequência varia por binning |
| **GPU** | Mali-400 ou Mali-450 | Depende da geração SoC |
| **RAM** | 1–2 GB (LPDDR3 ou DDR3) | Alguns modelos 512 MB ou 4 GB |
| **eMMC** | 8–32 GB (vendor varia) | Pode ser SD-only sem eMMC |
| **Ethernet** | 100 Mbps (não Gigabit) | Raro: Gigabit em high-end |
| **Wi-Fi** | Integrado ou USB externo | ESP8089, RTL8189, RTL8723 típicos |
| **HDMI** | HDMI 1.4 (up to 4K @ 30Hz) | Alguns apenas HD (1080p) |

### Como Localizar o Pad de Maskrom — V8.1

A revisão **V8.1 é significativamente posterior** às revisões V1–V3 do RK3229. Espere:

**Posição esperada do pad:**
- **Próximo ao eMMC ou CPU** (padrão Rockchip)
- **Via de teste pequena** (tipicamente 0.5–1.5 mm diâmetro)
- **Rotulada com silk**: "NAND_RE", "CLK", "MCLK", "DD", "TP_*" ou **nenhum rótulo visível**

**Se V8.1 é layout novo, pode estar em posição NOT encontrada em teardowns V1–V3:**

```
Estratégia: Testar vias próximas ao eMMC com multímetro
  1. Encontre o chip eMMC (silkscreen dirá "eMMC" ou será package grande)
  2. Teste cada via próxima: continuidade com GND?
  3. Rockchip sempre usa GND como referência para maskrom short
  4. Via correta: <1 Ohm quando shorted, ponto de entrada para BootROM
```

**Alternativa: Comunidade Rockchip**
- Procure em GitHub por "R3290_V8.1 schematic" ou "R3290 maskrom pad"
- Poste em XDA/Armbian com fotos claras da PCB (ambos lados)
- Comunidade responde rapidamente com pad location

---

## § 3. Determinar Imagem Armbian Correta

### O Problema Crítico

O guia RK3229 recomenda `Armbian rk322x-box`. Para R3290, você **NÃO pode usar a mesma imagem**.

**Por quê?** A imagem Armbian está compilada para um SoC específico:
- Bootloader (idbloader + u-boot.itb) é SoC-específico
- Device tree (DTB) define hardware (pinouts, clocks, drivers)
- Usar imagem errada = black screen ou infinite reboot loop

### Passo 1: Identificar SoC Exato

Siga **§1 Passo 0** acima para confirmar se é RK3288, RK3328, ou outro.

### Passo 2: Localizar Imagem Armbian Compatível

**Opção A: Imagem Oficial Armbian (Recomendada)**

```bash
# Acesse: https://www.armbian.com/download/?device=
# Procure pelo seu SoC:
#   - RK3288? → Buscar "rk3288" no Armbian board list
#   - RK3328? → Buscar "rk3328" 
#   - RK3329? → Provavelmente não suportado (raro)

# URLs típicas:
# https://archive.armbian.com/rk3288/archive/Armbian_24.02_Rk3288_bookworm_current.img.xz
# https://archive.armbian.com/rk3328/archive/Armbian_24.02_Rk3328_bookworm_current.img.xz

# Se seu device NÃO aparecer:
# → Consulte README de Armbian para seu SoC específico
# → Pode haver variants: rk3328-box, rk3288-generic, rk3288-tinker, etc.
```

**Opção B: Imagem Comunitária (Se Oficial Não Existe)**

```bash
# Procurar em:
# 1. GitHub armbian/build — issues com seu device
# 2. LibreELEC rk3288/rk3328 — builds da comunidade
# 3. FreakTab forums — Chinese community com builds custom
# 4. XDA Developers — custom Armbian ports

# Indicador de sucesso: Imagem terá nome como:
# Armbian_XX.XX_Rk3288_*
# Armbian_XX.XX_Rk3328_*
# (NOT "rk322x-box" — isso é RK3229 apenas)
```

### Passo 3: Verificar Compatibilidade Antes de Flash

```bash
# Após download, examine arquivos internos:
file Armbian_*.img.xz
# Expected: "XZ compressed data, checksum CRC32"

xz -d --keep Armbian_24.02_Rk3288_bookworm_current.img.xz
fdisk -l Armbian_24.02_Rk3288_bookworm_current.img
# Look for: "Boot" and "Linux" partitions (≥2 partitions)

# Extrair device tree para confirmar SoC:
mkdir /tmp/armbian_check
sudo loopback mount -o loop Armbian_24.02_Rk3288_bookworm_current.img /tmp/armbian_check
strings /tmp/armbian_check/boot/dtb-* | grep -i "rk328"
sudo umount /tmp/armbian_check
# Output deve mencionar seu SoC ("rk3288", "rk3328", etc.)
```

---

## § 4. Checklist Pré-Flashing (R3290 Específico)

| Item | Verificar | Status |
|------|-----------|--------|
| **SoC identificado** | RK3288 / RK3328 / outro? (§1, Passo 0) | ☐ |
| **Imagem Armbian baixada** | URL oficial Armbian ou comunidade (§3) | ☐ |
| **Checksum verificado** | `sha256sum` ou comparar site | ☐ |
| **rkdeveloptool instalado** | `rkdeveloptool --version` retorna número | ☐ |
| **libusb disponível** | `pkg-config --modversion libusb-1.0` | ☐ |
| **Cabo USB-OTG funcional** | Teste com outro device (§1 RK3229) | ☐ |
| **Pad de maskrom localizado** | Silk label ou via test confirmado | ☐ |
| **Máquina dev pronta** | Linux/macOS/WSL com rkdeveloptool | ☐ |
| **Backup feito** (if needed) | Se data importante está no device | ☐ |
| **Permissões sudo** | `sudo rkdeveloptool ld` funciona | ☐ |

---

## § 5. Entrar em Maskrom Mode — R3290_V8.1

### Sequência Idêntica ao RK3229 (Timing Crítico)

**Material**:
- Agulha descalibrada, jumper fino, ou stylus metálico
- Cabo USB-OTG
- Fonte 5V

**Procedimento**:

```bash
# Terminal 1 (máquina dev) — ANTES de qualquer ação no device:
sudo rkdeveloptool ld
# Comando fica pendente (sem output) — AGUARDE

# Terminal 2 ou simultâneo no device (2–3 segundos após comando acima):
# 1. Desligar completamente (remover fonte 5V)
# 2. Aguardar 5 segundos
# 3. Short o pad de maskrom com agulha/jumper (MANTER SHORTED)
# 4. Conectar cabo USB-OTG (se não já conectado)
# 5. Conectar fonte 5V (device liga)
# 6. Aguardar 3 segundos com short ativo
# 7. SOLTAR o short (ainda powered)
# 8. Aguardar outro 3 segundos

# Terminal 1 deve agora mostrar:
# DevNo=1	Vid=0x2207,Pid=0x330c,LocationID=XXX	Maskrom
# (ou similar — formato pode variar, mas "Maskrom" deve aparecer)
```

### Troubleshooting Maskrom Entry (R3290 Específico)

| Sintoma | Causa Provável | Solução |
|---------|---|---|
| `Found 0 devices` (timeout) | Pad não localizado corretamente | Reabrir device, testar múltiplas vias próximas ao eMMC com multímetro |
| `Found 0 devices` (rápido) | Timing errado | Tentar esperar 10 segundos APÓS conectar fonte antes de soltar short |
| Device not recognized by lsusb | Libusb permission ou cabo | Try `sudo`, different USB port, different cable |
| Maskrom found, then disappears | Device reset ou timeout | Tem ~3 segundos após boot para começar escrita; prosseguir direto para flash |

---

## § 6. Flashing Armbian — R3290_V8.1

### Procedimento Padrão Rockchip (Idêntico para Todos os SoCs)

```bash
# Pré-requisito: Device em maskrom mode (§5)
# Imagem Armbian correcta para seu SoC (§3)

# Passo 1: Decompress imagem (se ainda não feito)
xz -d Armbian_24.02_Rk3288_bookworm_current.img.xz
# Resultado: Armbian_24.02_Rk3288_bookworm_current.img (~2–3 GB)

# Passo 2: Flash (esta é a operação crítica)
sudo rkdeveloptool wl 0 Armbian_24.02_Rk3288_bookworm_current.img

# Expected output (leva 5–15 minutos):
# Writing data...
# Write LBA 0  [==================================================>] 100% TIME
# Write success

# Passo 3: Reboot
sudo rkdeveloptool rd
# Device desaparece de `rkdeveloptool ld` (sai de maskrom)
```

### Se Flash Falhar

```bash
# Erro: "Transfer Error", "Timeout", "Bad block"
# Recovery:

# 1. Re-enter maskrom (§5)
sudo rkdeveloptool ld

# 2. Full erase
sudo rkdeveloptool ef    # Leva 2–5 minutos

# 3. Retry flash
sudo rkdeveloptool wl 0 Armbian_24.02_Rk3288_bookworm_current.img

# Se AINDA falhar: Pode ser device corrompido
# → Try diferente cabo USB
# → Try porta USB diferente no PC
# → Try powered USB hub (device pode precisar mais power)
```

---

## § 7. Primeiro Boot & Verificação

### Comportamento Esperado Pós-Flash

```bash
# Desconectar máquina dev (USB opcional)
# Deixar fonte 5V conectada

# Ligue o device (2–3 minutos de boot esperado)
# Sinais normais:
#   - LED piscando/aceso (atividade)
#   - HDMI mostrando logo Armbian ou kernel messages
#   - Network começando a procurar DHCP

# Descobrir IP:
arp-scan --localnet | grep -i armbian
# ou verificar router DHCP leases

# SSH para device:
ssh root@192.168.1.XXX    # Substitua com IP
# Password: 1234 (padrão Armbian primeiro boot)
# Armbian solicitará trocar senha — faça isso
```

### Verificação Crítica do SoC

```bash
# ANTES de qualquer outra coisa, confirme que bootou com imagem CORRETA:

cat /proc/device-tree/model
# Expected: "rockchip,rk3288-*" ou "rockchip,rk3328-*" (match seu SoC)
# Se output for DIFERENTE: imagem errada foi flashed
#   → Re-enter maskrom, erase, reflash com imagem correta

uname -m
# Expected: armv7l (32-bit) ou aarch64 (64-bit)

dpkg --print-architecture
# Expected: armhf (32-bit) ou arm64 (64-bit)
```

---

## § 8. Post-Flash Security Verification

### 6 Checks Críticos (Idêntico ao RK3229)

Execute após Armbian boot, **ANTES** de conectar à rede de produção:

```bash
# Check 1: Nenhuma partition Android sobreviveu
sudo lsblk -o NAME,LABEL,FSTYPE | grep -Ei 'system|vendor|recovery|misc|frp|oem'
# PASS: (no output)
# FAIL: (qualquer match) → Re-flash, full erase, retry

# Check 2: Nenhuma file substitution (Vo1d style)
[[ -e /system ]] && echo "WARN: /system exists" || echo "PASS: clean"

# Check 3: Nenhum tráfego C2 ativo
ss -tnp 2>/dev/null | grep -Ei 'catmore88|ycxrl|duoduodev'
# PASS: (no output)

# Check 4: Baseline de rede
DEFAULT_IFACE=$(ip route show default | awk '{print $5; exit}')
sudo timeout 60 tcpdump -nn -i "$DEFAULT_IFACE" -c 200 not arp > /tmp/baseline.pcap
# Inspect em máquina dev:
tcpdump -r /tmp/baseline.pcap | head -20

# Check 5: Armbian release sanity
cat /etc/armbian-release | head -10
# Output deve incluir BOARD_NAME (rk3288, rk3328, etc.)

# Check 6: Kernel modules de source limpa
find /lib/modules/$(uname -r) -name '*.ko*' | xargs basename -a | sort -u | \
  grep -Eiv '^(rockchip|rk_|sun|brcm|rtl|mt|ath|cfg80211|mac80211|usb|nft|wireguard|cake|crypto|ext4|sd|mmc|scsi)' && echo "WARN" || echo "OK"
```

### Se Qualquer Check Falhar

```
⚠️  CRÍTICO: Não prosseguir com OpenBox installation

Recovery:
  1. Full erase: rkdeveloptool ef
  2. Reflash com imagem Armbian (confirme SoC correto)
  3. Retry § 8 completo

Se falhas persistem:
  - Armbian pode não suportar seu SoC específico
  - Device pode estar danificado
  - Contacte comunidade Armbian com output de § 7 "SoC verification"
```

---

## § 9. OpenBox Installation (Próximos Passos)

Uma vez que todos 8 checks passam:

```bash
# 1. Clone repositório OpenBox (se não já feito)
git clone https://github.com/seu-repo/openbox.git
cd openbox

# 2. Dry-run (recomendado)
sudo bash install.sh --dry-run

# 3. Execute instalação
sudo bash install.sh
# (30–45 minutos para full stack)

# 4. Referências:
# - docs/CASE_STUDY.md — visão completa
# - docs/THREAT_MODEL.md — o que OpenBox protege
# - docs/HARDENING_PLAN_v2.md — implementação
# - docs/RUNBOOK.md — operações dia-a-dia
```

---

## § 10. Troubleshooting — R3290 Específico

### USB Device Not Found After Maskrom Entry

```
Sintoma: rkdeveloptool ld fica pendente, sem "Maskrom" device

Checklist:
  1. Pad shorted continuamente durante 5+ segundos?
  2. Cabo USB está em porta direta (não hub)?
  3. Cabo é USB-OTG de dados (não power-only)?
  4. libusb instalado? (pkg-config --modversion libusb-1.0)
  5. Permissões sudo corretas?
  
Teste alternativo:
  - Conecte device SEM short, aguarde boot Android (se possível)
  - Verifique com `lsusb` que device é reconhecido
  - Isola problema: USB working vs. maskrom pad wrong
```

### Black Screen After Flash

```
Sintoma: LED aceso, mas HDMI preto

Causas:
  1. Imagem errada flashed (SoC mismatch)
  2. eMMC corrompido durante escrita
  3. Bootloader incompleto

Recovery:
  1. Re-enter maskrom (§5)
  2. Verify que imagem foi completamente escrita:
     sudo rkdeveloptool rd 0x0 1024 /tmp/test.bin
     hexdump -C /tmp/test.bin | head -5
     (Deve mostrar magic bytes bootloader, não 0x00000000)
  3. Se corrupto: full erase + reflash
  4. Serial console (Apêndice A) para debug detalhado
```

### Network Not Detected

```
Sintoma: Armbian boot, mas sem IP DHCP

Solução:
  1. Ethernet cable plugado?
  2. DHCP server na rede?
  3. Força DHCP renew:
     sudo dhclient -v eth0
  4. Configure IP estático:
     sudo ip addr add 192.168.1.100/24 dev eth0
     sudo ip route add default via 192.168.1.1
  5. Se ainda falha: driver Ethernet ausente em Armbian
     - Check com: ethtool eth0
     - Se "No such device": kernel module não carregou
     - Verify Armbian build support Rockchip Ethernet (depende do SoC)
```

### Device Brick Recovery

```
Improvável (maskrom sempre é recovery), mas:

1. Espere 30 minutos (deixe device descarregar)
2. Try maskrom entry novamente (§5)
3. Full erase (rkdeveloptool ef)
4. Reflash with correct image
5. If still no response: hardware dano real (raro)
```

---

## Apêndice A: Serial Console (Debug)

### Por Que Serial Console?

Se HDMI não funciona ou boot fica stuck, serial console mostra kernel messages em tempo real.

### Hardware Necessário

- USB-to-Serial adapter (CH340, PL2303, ou FT232)
- 3 jumpers ou fios para conectar TX, RX, GND
- Terminal software (minicom, picocom, ou screen)

### Localizar Serial Pins

R3290_V8.1 **provável** tenha header de debug:
- **3 pinos** ou **4 pinos** (GND, TX, RX, e possibly VCC)
- Localização: Tipicamente na borda PCB ou perto de CPU

```
Padrão Rockchip (maioria dos devices):
┌─────────────┐
│  GND  TX RX │  (pins podem estar em qualquer ordem)
│  ■    ■  ■  │
└─────────────┘
Voltage: 3.3V (NÃO 5V!)
```

**Se você não conseguir achar os pinos:**
- Procure em GitHub por "R3290 schematic" ou "R3290 UART pins"
- Post fotos de ambos lados da PCB em XDA/Armbian
- Comunidade identifica rapidamente

### Conectar Serial

```
USB-to-Serial Adapter:
  GND (preto) → GND pin na PCB
  TX (branco)  → RX pin na PCB (crossed!)
  RX (verde)   → TX pin na PCB (crossed!)
  
Nota: TX/RX são invertidos — isso é intencional (full-duplex UART padrão)
```

### Monitorar Boot

```bash
# Identificar device serial:
ls /dev/ttyUSB* /dev/ttyACM* /dev/ttyAMA*

# Abrir conexão (velocidade: 115200 8N1)
minicom -D /dev/ttyUSB0 -b 115200
# ou:
picocom -b 115200 /dev/ttyUSB0
# ou:
screen /dev/ttyUSB0 115200

# Boot Armbian via power-on
# Serial console mostrará kernel messages em tempo real
# Procure por "Rockchip" para confirmar SoC
# Procure por "EXT4" ou "mount" para ver status rootfs
```

---

## Apêndice B: Supply Chain Security — Ameaças R3290

### BadBox 2.0 (FBI PSA250605)

**Escala**: 10M+ devices Android TV boxes  
**Risco para R3290**: **MUITO ALTO** (device genérico Rockchip)

**Vetores**:
1. Pre-flash na fábrica (sua caixa provavelmente infectada)
2. First-boot OTA (Android contacta servidor malicioso)
3. Sideload via app store não-oficial

**Mitigação via OpenBox**:
- ✅ Wipe ANTES de qualquer tráfego de rede
- ✅ Flash via maskrom (contorna software pré-infectado)
- ✅ DNS sinkhole dos IoC domains via Pi-hole
- ✅ Kill switch nftables atomic (nenhum tráfego sem VPN)

---

### Vo1d (Doctor Web, 2024-09)

**Escala**: 1.3M Android TV boxes  
**Brasil**: #1 país infectado

**Mecanismo**: Substitui `/system/bin/debuggerd`; coloca `/system/xbin/vo1d` + `/system/xbin/wd`

**Mitigação**: Vo1d vive apenas em Android `/system` partition. Wipe + Armbian flash remove completamente.

---

## Apêndice C: Comunidade & Referências

### Onde Encontrar Ajuda

| Recurso | URL | Para Quê |
|---------|-----|----------|
| **Armbian** | https://www.armbian.com/ | Download imagens, support boards conhecidos |
| **Armbian Forums** | https://forum.armbian.com/ | Perguntas sobre R3290, device tree issues |
| **XDA Developers** | https://xda-developers.com/ | R3290 specific threads, custom ROMs |
| **LibreELEC** | https://libreelec.tv/ | Alternativa para streaming (Kodi-based) |
| **FreakTab** | https://www.freaktab.com/ | Comunidade chinesa, Android TV box expertise |
| **GitHub** | https://github.com/ search "R3290" | Schematics, device trees, custom builds |
| **Rockchip Wikis** | https://opensource.rock-chips.com/ | Technical specs, maskrom procedures |

### Próximos Passos

1. **Confirmar SoC exato** (§1 Passo 0)
2. **Encontrar imagem Armbian correta** (§3)
3. **Localizar pad de maskrom** (§2 ou comunidade)
4. **Seguir procedimento §5–§8**
5. **Post resultado em Armbian forums** (feedback para comunidade)

---

## Histórico de Revisões

| Versão | Data | Status |
|--------|------|--------|
| 1.0 | 2026-04-25 | Inicial: framework adaptável para R3290_V8.1 (documentação incompleta, requer confirmação de SoC) |

---

**NOTA IMPORTANTE**

Este guia foi criado como **estrutura robusta** para o R3290_V8.1, um device pouco documentado. O procedimento (maskrom → rkdeveloptool → Armbian) é universalmente Rockchip, MAS:

- ❓ **Confirmação necessária**: Qual é o SoC exato? (RK3288, RK3328, outro?)
- ❓ **Imagem certa**: Qual é a build Armbian compatível?
- ❓ **Pad location**: Onde fica o maskrom pad em V8.1?

**Você deve colaborar com a comunidade** (XDA, Armbian, GitHub) para consolidar estes detalhes. Uma vez confirmados, este guia pode ser expandido para um documento completo e definitivo, como foi feito para RK3229.

**Contribuições bem-vindas**: Se você completar o procedimento com sucesso, poste em Armbian forums + GitHub com:
- Fotos da PCB (ambos lados)
- Output de `cat /proc/device-tree/model`
- Imagem Armbian que funcionou
- Qualquer modificação necessária

A comunidade Rockchip é ativa e colaborativa. Seu feedback ajuda outros usuários com R3290.
