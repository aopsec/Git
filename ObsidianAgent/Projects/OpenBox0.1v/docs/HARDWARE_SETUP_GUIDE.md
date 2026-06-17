# Guia Completo de Setup & Boot — RK3229 (R29_5G_LP3)

> **Retarget OpenBox v0.2.0 para Rockchip RK3229**  
> Procedimento de identificação, formatação e bootstrap de caixa Android genérica para Armbian  
> Versão: 1.0 · Data: 2026-04-25

---

## § 1. Introdução

### O que este guia cobre

Este documento guia você através do processo **completo** de transformar um TV box genérico (modelo R29_5G_LP3, SoC Rockchip RK3229) de seu estado de fábrica (Android proprietary pré-infectado) para um ambiente limpo, auditável e pronto para OpenBox v0.2.0.

**Fluxo**: Identificação do hardware → Preparação da máquina dev → Entrada em maskrom mode (recuperação de hardware) → Flash da imagem Armbian via USB-OTG → Verificação pós-flash → Próximos passos (instalação OpenBox).

### O que NÃO está coberto

- Instalação de OpenBox v0.2.0 — vide `install.sh` e `docs/HARDENING_PLAN_v2.md`
- Adição de disco encriptado (LUKS) — fora do escopo v0.1
- Alteração de bootloader ou U-Boot — requer conhecimento especializado (Rockchip SDK)
- Alternatives non-Armbian (LibreELEC, OSMC) — este guia é Armbian-específico

### Pré-requisitos de hardware

| Item | Especificação | Por quê |
|------|---------------|---------|
| **Caixa RK3229** | R29_5G_LP3 (genérico, qualquer marca white-label) | Sujeito deste guia |
| **Cabo USB-OTG** | USB-A (macho) ↔ Micro-USB (macho), com suporte data + power | Comunicação maskrom com dev machine |
| **Máquina dev** | Linux/macOS/WSL com rkdeveloptool + libusb | Flash da imagem Armbian |
| **Fonte 5V** | Qualquer fonte USB padrão | Alimentação durante flashing |
| **Jumper / agulha** | Opcional, para shortar pad de maskrom | Se pad não acessível com 2 dedos |
| **Cabo de rede** | RJ45, para primeiro boot | DHCP IP allocation em Armbian |
| **Tempo** | 30–60 minutos (incluindo troubleshooting) | Expectativa realista |

### Por que isso importa: Ameaças de supply-chain

Sua caixa **provavelmente foi compromised na fábrica**. Dois malwares específicos visam este device class:

| Malware | Escala | Vetor | Mitigação |
|---------|--------|-------|-----------|
| **BadBox 2.0** | 10M+ devices (FBI PSA250605) | Pre-boot OTA após primeiro boot (não conectar a rede antes de wipar) | Wipe + flash via maskrom antes de qualquer tráfego |
| **Vo1d** | 1.3M Android TV boxes, Brasil #1 (Doctor Web) | Instalado no `/system` partition (Android) | Wipe completo remove; não infecta BootROM |

**Ação crítica**: Nunca ligue o TV box em NENHUMA rede enquanto estiver rodando Android. O vetor de primeira execução (first-boot OTA) é automático.

### Glossário

| Termo | Significado |
|-------|-------------|
| **Maskrom mode** | Modo de recuperação de hardware (BootROM), ativado por hardware (short de pad). Permite flash completo de eMMC sem dependência do software existente. |
| **rkdeveloptool** | Ferramenta FOSS (código aberto) para communicate com Rockchip devices em maskrom. |
| **Armbian** | Distribuição Linux lightweight para SBCs (Single Board Computers) e TV boxes; mantida por comunidade. Imagem rk322x-box suporta nosso PCB. |
| **eMMC** | Embedded MultiMediaCard; armazenamento interno do TV box (não removível como SD). |
| **Bootloader** | Software que roda entre BootROM (silicon) e kernel Linux. Dividido em: SPL (idbloader), U-Boot, OP-TEE (trusted execution). |
| **Phase 0** | Verificação de hardware pós-boot (capturas 12 facts; 4 gate criteria). Executada pelo script `fingerprint-rk3229.sh`. |

---

## § 2. Identificação de Hardware

### Como reconhecer sua caixa

A maioria dos TV boxes RK3229 é vendida sob marcas diferentes (MXQ Pro 4K, R29_5G_LP3, etc.), mas compartilham a mesma placa de circuito. Identificar sua revisão PCB garante que os procedimentos de maskrom e drivers estejam corretos.

**Passos**:
1. Abra a caixa (tipicamente via parafusos na parte traseira ou clips de plástico)
2. Procure por **silk-screen labels** na PCB (gravação branca/preta)
3. Procure por um label como "**V1.1**", "**V2.3**", "**V3.0**" (versão do layout)
4. Verifique o chip de armazenamento (veja próxima seção)

### Revisões PCB conhecidas

| Revisão | Maskrom Pad | Localização no PCB | eMMC | DRAM | Issues Conhecidas |
|---------|-------------|-------------------|------|------|-------------------|
| **V1.1** | Silk: "U4" via em canto SW | Bottom-left, abaixo do eMMC | NANYA NT5CB256M16CP-D1 (2 GB?) | LPDDR3 1 GB | Pad pequeno, soldagem frágil; test pad via preferível |
| **V1.2** | Silk: "MCLK" ou "DD" via | Right side do eMMC (pode estar coberto por rótulo) | Kingston/Samsung 8–16 GB | LPDDR3 1 GB | Pad mais acessível; via é padrão |
| **V2.3** | Silk: "NAND_RE" ou "CLK" (TP label) | Acima da DRAM, centro-direita | Varia (Kingston, Apacer, Sandisk) | LPDDR3 1 GB | Design mais robusto; pad bem documentado em teardowns |
| **V3.0** | **N/A** (maskrom não acessível) | Não mapeado em comunidade | Varia | LPDDR3 | Firmware pré-versionado; não recomendado para flashing manual. Unlikely em market atual. |

### Localizando o pad de maskrom (com diagramas ASCII)

O pad de maskrom permite entrar em modo de recuperação, contornando qualquer software existente.

#### V1.2 (mais comum em AliExpress/Shopee 2025–2026)

```
                    USB Connectors (top edge)
                         ↓
    ┌─────────────────────────────────────┐
    │  Ethernet    USB-A        USB-A      │
    │    Jack      Host         Host       │
    ├─────────────────────────────────────┤
    │                                      │
    │  [CPU Heatsink]                      │ ← Remove if blocking
    │                                      │
    │  ┌─────────┐         ┌─────────┐    │
    │  │  eMMC   │         │  Power  │    │
    │  │         │         │ Mgmt IC │    │
    │  └─────────┘         └─────────┘    │
    │         ↑ (V1.2 pad here,             │
    │         right side,                  │
    │         small circle)                │
    │  ┌─────────┐                         │
    │  │  DRAM   │                         │
    │  │         │                         │
    │  └─────────┘                         │
    │                                      │
    │            [Various test vias]       │
    │  (Silk labels: "DD", "MCLK", etc)    │
    │                                      │
    ├─────────────────────────────────────┤
    │ Back (where sd card slot is)         │
    └─────────────────────────────────────┘
```

**Método prático**: 
- Localize o chip eMMC (retângulo preto maior, tipicamente 16 × 12 mm)
- Procure por um pequeno círculo/via à direita do eMMC
- Rótulo silk pode ser "MCLK", "DD", "NAND_RE", ou nenhum rótulo visível
- Via é minúscula (≈ 0.5 mm de diâmetro); use agulha descalibrada ou jumper fino

#### V2.3 (segunda mais comum)

```
                    CPU Heatsink (removível)
                              ↓
    ┌─────────────────────────────────────┐
    │  Ethernet                            │
    │    ┌─────────────┐                   │
    │    │ Heatsink    │                   │ ← Cobertura para maskrom
    │    │ ┌─────────┐ │   ╔═══════════╗  │
    │    │ │  eMMC   │ │   ║ Maskrom   ║  │
    │    │ │  16 GB  │ │ ← ║ Pad (V2.3)║  │ Center-right, easy to access
    │    │ └─────────┘ │   ╚═══════════╝  │
    │    └─────────────┘                   │
    │                                      │
    │    ┌─────────────┐                   │
    │    │    DRAM     │                   │
    │    │  (LPDDR3)   │                   │
    │    └─────────────┘                   │
    │                                      │
    ├─────────────────────────────────────┤
    │           Micro USB OTG (bottom)     │
    └─────────────────────────────────────┘
```

**Método prático**:
- Remove heatsink (tipicamente cola ou preso com parafuso M2)
- Pad é visível acima da DRAM, ligeiramente à direita do centro
- Rótulo silk "NAND_RE" ou "CLK" próximo
- Via é maior que V1.1 (≈ 1 mm)

### Identificar vendor do eMMC

O vendor do armazenamento é importante para diagnóstico de problemas. Procure no chip labels legíveis:

**Exemplos**:
- NANYA NT5CB256M16CP-D1 (2 GB) → "NANYA" gravado
- Kingston (8 GB) → "Kingston" + modelo
- Sandisk / WD (16 GB) → "Sandisk" ou "WD"
- Apacer (8 GB) → "Apacer"

Anote o vendor para referência durante troubleshooting (alguns vendors têm issues de timing com rkdeveloptool).

---

## § 3. Checklist Pré-Flashing

### Máquina dev: Requisitos

| Requisito | Mínimo | Teste |
|-----------|--------|-------|
| **SO** | Linux (Ubuntu 20.04+, Debian 11+) ou macOS 10.14+ ou WSL2 | `uname -s` |
| **libusb** | 1.0.9+ | `pkg-config --modversion libusb-1.0` |
| **rkdeveloptool** | Latest | `rkdeveloptool --version` |
| **ca-certificates** | Atual | `curl https://ifconfig.io >/dev/null 2>&1` |
| **Permissões USB** | sudo ou udev rules | `sudo rkdeveloptool ld` (funciona) |

### Instalar rkdeveloptool

#### Linux (Ubuntu/Debian)

```bash
# Opção 1: from apt (mais simples, pode ser desatualizado)
sudo apt update
sudo apt install -y rkdeveloptool libusb-1.0-0-dev

# Opção 2: from source (latest, recomendado)
sudo apt install -y build-essential libusb-1.0-0-dev
git clone https://github.com/rockchip-linux/rkdeveloptool.git
cd rkdeveloptool && autoreconf -i && ./configure && make -j4
sudo make install
sudo ldconfig

# Verificar
rkdeveloptool --version
# Expected output: rkdeveloptool ver 1.32 (pode variar)
```

#### macOS (via Homebrew)

```bash
brew install libusb rkdeveloptool
rkdeveloptool --version
```

#### WSL2 (Windows Subsystem for Linux)

```bash
# WSL2 com USB: requer usbipd-win; mais complexo
# Alternativa simples: use RKDevTool GUI no Windows (vide § 5)

# Se quiser WSL2 + USB:
sudo apt install -y rkdeveloptool libusb-1.0-0-dev
# Conectar USB via PowerShell:
# PS> usbipd list
# PS> usbipd bind -b <BUSID>
# PS> usbipd connect -b <BUSID> -w
```

### Download & Verificação de Imagem Armbian

**Imagem recomendada**: Armbian `rk322x-box` (latest stable).

```bash
# 1. Download de fonte oficial
cd /tmp
wget https://archive.armbian.com/rk322x-box/archive/Armbian_24.02_Rk322x-box_bookworm_current.img.xz

# 2. Verificar checksum (find on Armbian website)
echo "abcd1234... Armbian_24.02_Rk322x-box_bookworm_current.img.xz" | sha256sum -c -
# Expected: OK

# 3. Decompress
xz -d Armbian_24.02_Rk322x-box_bookworm_current.img.xz
# Resultado: Armbian_24.02_Rk322x-box_bookworm_current.img (~2–3 GB)
```

### Verificação cabo USB-OTG

Cabos USB-OTG baratos frequentemente têm apenas power, não data. Teste antes:

```bash
# 1. Conecte cabo em uma porta USB do PC (sem TV box no outro lado)
# 2. Verifique device tree USB:
lsusb
# Se nada aparecer, cabo é power-only; tente outro.

# 3. Teste com outro device (ex: Phone com USB-OTG)
lsusb
# Deve mostrar algo como "Bus 001 Device 123: ID xxxx:yyyy"
```

---

## § 4. Entrar em Maskrom Mode

### Preparação

1. **Desligar TV box** completamente (remova fonte, aguarde 10 segundos)
2. **Remover heatsink** (se V2.3 e cobrindo pad)
3. **Localizar pad de maskrom** (use tabela § 2 conforme sua revisão)
4. **Preparar jumper ou agulha** para shortar pad
5. **Máquina dev** com rkdeveloptool instalado e testado

### Sequência de Maskrom Entry (V1.2 / V2.3)

**TIMING é crítico**. O device enumera por apenas ~3 segundos após BootROM ativar.

```bash
# Passo 1: Prepare a máquina dev
# Terminal 1 (deve estar pronto ANTES de ligar a caixa):
sudo rkdeveloptool ld    # Este comando vai pendente até device appear
# (Não vai output nada por ~15 segundos)

# Passo 2: Simultaneamente, no TV box (2–3 segundos após rkdeveloptool ld):
# - Short o pad de maskrom com agulha/jumper (manter shorted!)
# - Conecte cabo USB-OTG (com source já conectada a USB-A do PC, Micro-USB ao TV box)
# - Ligue a fonte 5V (TV box ligar)

# Passo 3: Aguarde 3 segundos, solte o short do pad

# Passo 4: Na terminal 1, rkdeveloptool ld deve output algo:
# Expected output:
# DevNo=1	Vid=0x2207,Pid=0x330c,LocationID=101	Maskrom
```

### Decision Tree: Maskrom Entry Troubleshooting

```
┌─ rkdeveloptool ld outputs "Maskrom" device?
├─ YES → Go to § 5 (Flashing)
└─ NO → "Found 0 devices"
   │
   ├─ Check 1: Cabo USB está bem conectado?
   │  └─ Try different USB port on PC; avoid hubs
   │
   ├─ Check 2: libusb permissions?
   │  └─ sudo rkdeveloptool ld
   │     or: sudo usermod -a -G plugdev $USER && logout/login
   │
   ├─ Check 3: Pad de maskrom está sendo shorted?
   │  └─ Verifique com multímetro: continuidade entre pad e GND
   │     Expected: <1 Ohm quando shorted
   │
   ├─ Check 4: Timing errado?
   │  └─ Aguarde rkdeveloptool ld estar pendente ANTES de shortar
   │     Ligue a fonte ENQUANTO mantém short
   │
   ├─ Check 5: Pad errado / revisão incorreta?
   │  └─ Re-consulte tabela § 2 pela sua revisão PCB
   │     Procure por via perto do eMMC; silk label pode ajudar
   │
   └─ Check 6: TV box brick permanente?
       └─ Teoricamente improvável (maskrom é silicon-level)
          Tente esperar 30 min, repetir com cabo diferente
```

### Se rkdeveloptool ld funcionar

```bash
# Verificar informações do device
sudo rkdeveloptool ld
# Output esperado:
# DevNo=1	Vid=0x2207,Pid=0x330c,LocationID=101	Maskrom

# Prosseguir para § 5 (Flashing)
```

---

## § 5. Flashing Armbian via rkdeveloptool

### Visão geral do procedimento

O flash consiste em 3 passos:
1. **Write bootloader** (idbloader + u-boot.itb) → setor 0x40
2. **Write root filesystem** (Armbian image) → resto da eMMC
3. **Verificação básica** (LED, tela)

### Estrutura de arquivo Armbian

Antes de começar, o arquivo Armbian precisa estar descompactado:

```bash
ls -lh Armbian_24.02_Rk322x-box_bookworm_current.img
# Expected: ~2.5 GB file, not .xz compressed
```

### Flash com rkdeveloptool

**ADVERTÊNCIA**: Não interrompa durante escrita. Se desconectar USB ou perder poder, o eMMC fica em estado corrupto. Recovery requer re-entry em maskrom e full erase.

```bash
# Passo 1: Extrair bootloader da imagem Armbian
# (Armbian images já contêm bootloader nos primeiros setores)
# Não é necessário extrair separadamente para rk322x-box.
# Rkdeveloptool detecta automaticamente.

# Passo 2: Write boot + root filesystem
sudo rkdeveloptool wl 0 Armbian_24.02_Rk322x-box_bookworm_current.img

# Expected output (levará 5–15 minutos para eMMC de 8–16 GB):
# Writing data...
# Write LBA 0 [==================================================>] 100% TIME
# Write success

# Passo 3: Reboot para verificar
sudo rkdeveloptool rd
# Expected: Device desaparece de rkdeveloptool ld (maskrom mode sai)
```

### Possíveis erros durante flash

| Erro | Causa | Solução |
|------|-------|---------|
| `Transfer Error` | Timeout USB ou cabo solto | Reconecte cabo, re-enter maskrom, retry |
| `Bad block` | eMMC danificado (raro) | Try full erase: `rkdeveloptool ef`, então retry flash |
| `Write timeout` | Device muito lento (unlikely) | Esperar 30 min, tentar novamente |
| `Permission denied` | libusb sem permissão | Use `sudo`; ou configure udev rules |

### Full erase (se necessário)

Se algo der errado durante escrita, full erase pode recuperar:

```bash
# Re-enter maskrom (siga § 4 novamente)
sudo rkdeveloptool ef        # ef = erase flash
# Levará 2–5 minutos para eMMC inteira

# Depois, retry flash:
sudo rkdeveloptool wl 0 Armbian_24.02_Rk322x-box_bookworm_current.img
```

### RKDevTool (alternativa GUI para Windows)

Se preferir GUI em vez de linha de comando:
1. Download RKDevTool do Rockchip (proprietary, Windows only)
2. Interface gráfica para write bootloader + image
3. Documentação: [https://github.com/rockchip-linux/rkdeveloptool](https://github.com/rockchip-linux/rkdeveloptool) (referências Windows tools)

Não duplicamos Windows GUI steps aqui; manuals estão na comunidade Rockchip.

---

## § 6. Primeiro Boot & Verificação de Hardware

### Comportamento esperado pós-flash

```bash
# Passo 1: Desconecte a máquina dev (USB, se desired)
# Deixe a fonte 5V conectada ao TV box

# Passo 2: Ligue o TV box
# Expected behavior (30–60 segundos):
#   a) LEDs pode piscar (atividade de boot)
#   b) HDMI pode mostrar logo Armbian ou output kernel boot messages
#   c) Login prompt aparece (ou getty solicita login)
#   d) Network inicia (Ethernet buscando DHCP)

# Passo 3: Conecte à rede (Ethernet recomendado)
# Aguarde ~30 segundos para DHCP assignment

# Passo 4: Login (default Armbian credentials)
# Username: root
# Password: 1234
#
# Armbian vai solicitar senha nova no primeiro login. Configure uma forte.
```

### Descobrir IP do device

Se conseguir HDMI output, IP aparece no boot. Senão:

```bash
# Da máquina dev (após Armbian boot ~60 segundos):
arp-scan --localnet 2>/dev/null | grep -i armbian
# Ou:
nmap -sn 192.168.1.0/24 | grep -i rockchip

# Ou: verifique seu router DHCP lease table
# Procure por "Armbian" ou "rockchip" nos connected devices
```

### SSH para device

```bash
ssh root@192.168.1.XXX      # Substitua com IP descoberto
# Password: a que você criou no primeiro login

# Verifique que está em Armbian:
uname -a
# Expected: Linux openbox 5.15.x ... armv7l GNU/Linux (ou similar)
cat /etc/os-release | grep PRETTY_NAME
# Expected: PRETTY_NAME="Armbian 24.02 bookworm"
```

### Executar Phase 0 Hardware Fingerprint

O script `fingerprint-rk3229.sh` captura 12 facts do device e verifica 4 gate criteria obrigatórias.

```bash
# Copie o script para device (ou dentro do OpenBox clone):
cd /path/to/openbox/git
sudo bash tools/fingerprint-rk3229.sh > docs/hw/r29_5g_lp3.txt 2>&1

# Ou run remotamente:
ssh root@192.168.1.XXX "cd /root/openbox && bash tools/fingerprint-rk3229.sh"
```

### Phase 0 Gate Criteria (4 checks obrigatórios)

Abra `docs/hw/r29_5g_lp3.txt` e verifique as 4 seções abaixo. **Todas** devem passar:

#### 1. SoC correto (Seção 0.1)

```
/proc/device-tree/model
├─ PASS: rockchip,rk3229-xxx
└─ FAIL: qualquer outro (ex: allwinner, amlogic, etc.)
```

Se FAIL: Wrong Armbian image foi flashed. Download `rk322x-box` especificamente.

#### 2. Arquitetura armhf (Seção 0.2)

```
uname -m                    → armv7l
dpkg --print-architecture   → armhf
```

Se FAIL: Imagem é 64-bit (arm64) ou x86. Não compatível. Reflash com image armv7l.

#### 3. WireGuard kernel module (Seção 0.7)

```
modinfo wireguard
├─ PASS: (output com "filename:", "version:", etc.)
└─ FAIL: ERROR: modinfo: ERROR: Module wireguard not found
```

Se FAIL: Instale: `sudo apt install -y wireguard wireguard-tools linux-modules-extra-$(uname -r)`

#### 4. Watchdog device (Seção 0.10)

```
ls -l /dev/watchdog*
├─ PASS: /dev/watchdog0, /dev/watchdog1, etc. (at least 1)
└─ FAIL: No such file or directory
```

Se FAIL: Watchdog não está habilitado no kernel. Improvável em Armbian rk322x-box; tente:
```bash
sudo modprobe dw_wdt      # Rockchip watchdog driver
ls /dev/watchdog*         # Verify
```

### If any gate check fails

```bash
# ABORT OpenBox installation (Phase 1+)
# Possível solução:
# 1. Verifique você tem a imagem CORRETA: "rk322x-box"
# 2. Reflash:
#    - Re-enter maskrom (§ 4)
#    - Full erase: sudo rkdeveloptool ef
#    - Flash imagem diferente: sudo rkdeveloptool wl 0 Armbian_...img
# 3. Retry Phase 0

# Se todos 4 checks passam: Prosseguir para § 7
```

---

## § 7. Verificação de Segurança Pós-Flash

Antes de conectar o device em sua rede de produção, execute 6 verificações de segurança para confirmar que o wipe removeu todo malware de Android.

### 1. Nenhuma partition Android sobreviveu

```bash
# Expected: Apenas partições Armbian (mmcblk1p1=boot, mmcblk1p2=root)
sudo lsblk -o NAME,LABEL,FSTYPE | grep -Ei 'system|vendor|recovery|misc|frp|oem|trust'

# PASS: (no output — nenhuma Android partition)
# FAIL: (output com "system", "vendor", etc.)
```

Se FAIL: Flash foi incompleto. Full erase + reflash (§ 5).

### 2. Nenhuma file substituição Vo1d

```bash
# Vo1d renames /system/bin/debuggerd para debuggerd_real
# Armbian não tem /system path, mas check anyway:
[[ -e /system ]] && echo "WARN: /system exists" || echo "PASS: no /system path"
```

### 3. Nenhum tráfego C2 para BadBox / Vo1d

```bash
# Verifique estado de socket (nenhuma conexão ativa para C2 domains)
ss -tnp 2>/dev/null | grep -Ei 'catmore88|ycxrl|duoduodev|flyermobi|motiyu|qazwsxedc'

# PASS: (no output)
# FAIL: (conexão ativa para um dos domains — improvável em Armbian clean)
```

### 4. Baseline de tráfego de rede

```bash
# Capture 60 segundos de tráfego (antes de instalar OpenBox):
DEFAULT_IFACE=$(ip route show default | awk '{print $5; exit}')
sudo timeout 60 tcpdump -nn -i "$DEFAULT_IFACE" -c 200 not arp and not stp and not '(udp port 5353)' > /tmp/baseline.pcap

# Inspecione para destinos inesperados:
tcpdump -r /tmp/baseline.pcap | awk '{print $3}' | sort -u
# Deve incluir: gateway, DNS, NTP
# Não deve incluir: C2 domains, Android services
```

### 5. Armbian release sanity

```bash
cat /etc/armbian-release | head -10
# Expected output:
# BOARD=rk322x-box
# BOARD_NAME="Rockchip RK3229"
# BUILD_REPOSITORY_URL="https://github.com/armbian/build"
# BUILD_DATE="..."
```

Se BOARD ≠ rk322x-box: Wrong image. Reflash.

### 6. Kernel modules de source limpa

```bash
# Verifique que nenhum out-of-tree blobs estão carregados
# (Malware às vezes injecta .ko files)
find /lib/modules/$(uname -r) -name '*.ko*' | xargs -I{} basename {} .ko | sort -u | grep -Eiv '^(rockchip|rk_|sun[0-9]+|brcm|rtl|mt[0-9]+|ath|cfg80211|mac80211|usb|nft|ip|sch|cls|wireguard|cake|fou|fou6|ipt|xt|nf|crypto|aes|sha|gcm|chacha|poly|ext4|fat|vfat|nls_|usbcore|hid|input|drm|gpu|i2c|spi|uart|tty|serial|loop|md|raid|btrfs|f2fs|squashfs|fuse|nfs|cifs|isofs|cdrom|sd|mmc|scsi|sr|dm|tun|tap|veth|bridge|vxlan|gre|geneve|bonding|8021q|gpio|pwm|leds|hwmon|thermal|cpufreq|cpuidle|power|reboot|rtc|wd|watchdog|snd|sound|video|media|v4l|uvc|alsa|sof|ac97|spdif|fb|backlight|panel|hdmi|edp|dp|mipi|dsi|csi|isp|cif|vpu|rga|iep|vdec|venc|jpeg|h264|h265|vp8|vp9|av1)$'

# PASS: (no output)
# FAIL: (unexpected modules listed — investigate origin)
```

### Se qualquer verificação falhar

```
⚠️  CRÍTICO: Não prossiga com instalação de OpenBox.

Provável causa: Flash incompleta ou imagem corrompida.

Ação:
  1. Full erase (rkdeveloptool ef)
  2. Re-flash imagem (rkdeveloptool wl 0 ...)
  3. Retry § 7 completo
  
Se persiste: Armbian ou device podem estar danificados. 
Considere reflashar com imagem Armbian alternativa (ex: desktop variant)
ou contactar comunidade Rockchip.
```

Se TODOS 6 checks passam → Proceed para § 8.

---

## § 8. Próximos Passos: Instalação OpenBox

Parabéns! Seu TV box agora está limpo e rodando Armbian. Próxima fase é instalar OpenBox v0.2.0.

### Preparação final

```bash
# 1. Atualize pacotes (já deve estar feito, mas não custa):
sudo apt update
sudo apt upgrade -y

# 2. Prepare para instalação OpenBox
# Clone or download do repositório OpenBox (if not already done):
cd /root
git clone https://github.com/yourusername/openbox.git  # Substitua com URL correcta
cd openbox

# 3. Dry-run do install (recomendado):
sudo bash install.sh --dry-run
# Lê o que seria feito sem fazer nada

# 4. Se happy com dry-run, execute instalação:
sudo bash install.sh
# Levará 30–45 minutos (cria network namespace, WireGuard, Pi-hole, Tor, Stremio, etc.)
```

### Arquivos importantes

| Arquivo | Propósito |
|---------|-----------|
| `docs/CASE_STUDY.md` | Visão completa de problema + solução + arquitetura |
| `docs/THREAT_MODEL.md` | O que OpenBox protege / não protege |
| `docs/HARDENING_PLAN_v2.md` | Detalhes de implementação (nftables, WireGuard, Tor, DNS) |
| `docs/RUNBOOK.md` | Operações dia-a-dia (health checks, troubleshooting) |
| `install.sh` | Orquestrador de instalação (corre install.d/NN-*.sh) |

### Links para referência

- **RK3229 Threat Research**: `docs/security/RK3229_THREAT_RESEARCH.md`
- **Hardware Fingerprint**: `tools/fingerprint-rk3229.sh`
- **OpenBox CLAUDE.md**: `CLAUDE.md` (este repo)

---

## § 9. Guia de Troubleshooting

Problemas comuns durante flashing, boot ou verificação pós-flash.

### ❌ "USB device not found" (rkdeveloptool ld não acha device)

**Sintoma**: Terminal fica pendente; rkdeveloptool não output "Maskrom"

**Checklist**:
1. ✅ Cabo USB está plugado (TV box Micro-USB e PC USB-A)?
2. ✅ Outro cabo USB teste (alguns cabos USB-OTG são power-only)?
3. ✅ Pad de maskrom está sendo shorted (multímetro: <1 Ohm a GND)?
4. ✅ Timing correto (rkdeveloptool ld pendente ANTES de shortar pad)?
5. ✅ sudo permissions (try: `sudo rkdeveloptool ld`)?
6. ✅ libusb installed (`pkg-config --modversion libusb-1.0`)?
7. ✅ USB port diferente no PC (evite hubs)?

**Se ainda não funciona**:
```bash
# Debug via dmesg:
sudo dmesg | tail -20
# Look for "usb N-N: new high-speed USB device"
```

---

### ❌ "Maskrom entry fails" (pad não shorted ou errado)

**Sintoma**: Mesmo com rkdeveloptool ld correndo, device não aparece após shortar pad

**Checklist**:
1. ✅ Revisão PCB identificada corretamente (tabela § 2)?
2. ✅ Pad localizado (próximo a eMMC, silk label confere)?
3. ✅ Short é sólido (agulha/jumper faz contato, não está solto)?
4. ✅ Aguardar 10+ segundos com short antes de soltar (BootROM lento)?
5. ✅ Tentou aguardar APÓS shortar antes de rodar rkdeveloptool (timing)?

**Se ainda não funciona**:
- Pad pode estar em revisão PCB diferente. Reabra caixa, reidentifique (§ 2)
- Procure por via alternativa (alguns designs têm múltiplas rotas para maskrom)
- Considere RKDevTool GUI (Windows) como alternativa

---

### ❌ "Flash timeout" ou "Write interrupted"

**Sintoma**: rkdeveloptool wl inicia mas para no meio; output "Transfer error"

**Checklist**:
1. ✅ Cabo USB conectado solidamente?
2. ✅ Fonte 5V conectada ao TV box?
3. ✅ Nenhuma interrupção de power durante flash (esperado: 5–15 min)?
4. ✅ USB port diferente no PC?
5. ✅ Try slower rkdeveloptool variant (se existir)?

**Recovery**:
```bash
# Re-enter maskrom (§ 4)
# Full erase:
sudo rkdeveloptool ef    # Leva 2–5 min

# Retry:
sudo rkdeveloptool wl 0 Armbian_24.02_Rk322x-box_bookworm_current.img
```

---

### ❌ "Boot fails / Black screen" (nenhuma saída HDMI após flash)

**Sintoma**: TV box ligado (LED aceso), mas HDMI preto e sem tela de boot

**Checklist**:
1. ✅ eMMC foi flashed completamente (try verify):
   ```bash
   sudo rkdeveloptool rd 0x0 1024 /tmp/test.bin 2>/dev/null && hexdump -C /tmp/test.bin | head -5
   # Deve output código Armbian bootloader (magic bytes)
   ```
2. ✅ Imagem Armbian estava correta (`rk322x-box` no filename)?
3. ✅ Suportar HDMI (TV/monitor ligado, cabo HDMI plugado)?
4. ✅ Esperar 1–2 minutos de boot (Armbian pode ser lento primeira vez)?

**Se still black**:
- Try serial console (opcional; vide Appendix A)
- Full erase + reflash com imagem Armbian alternativa
- Considere device brick (improvável, mas maskrom sempre é recovery)

---

### ❌ "Network não detectada" (sem DHCP no primeiro boot)

**Sintoma**: Armbian boots (consegue SSH?), mas no tty "no IP address"

**Checklist**:
1. ✅ Cabo Ethernet plugado (durante boot)?
2. ✅ DHCP server na rede (router ligado)?
3. ✅ Roteador DHCP não bloqueando MAC addresses?

**Solução**:
```bash
# Após Armbian boot, forçar DHCP renew:
sudo dhclient -v eth0

# Ou configure IP estático:
sudo ip addr add 192.168.1.100/24 dev eth0
sudo ip route add default via 192.168.1.1 dev eth0
```

---

### ❌ "Phase 0 gate check fails"

Vide § 6, "If any gate check fails" section.

---

### ⚠️  "Full brick?" (nada responde)

**Improvável**, pois maskrom é interna ao BootROM (silicon). Mas se device está completamente não-responsivo:

```bash
# Último recurso: retry maskrom entry (§ 4) após esperar 30 min
# Então full erase + reflash

# Se mesmo isso não funciona: device pode ter dano hardware real (raro)
# Contacte comunidade Rockchip ou considerare device irrecuperável
```

---

## Apêndice A: Referência Técnica

### R29_5G_LP3 / RK3229 Specs

| Componente | Especificação |
|-----------|---|
| **SoC** | Rockchip RK3229, ARMv7 (32-bit) |
| **CPU** | Cortex-A7 Quad-core @ 1.3 GHz |
| **GPU** | Mali-400 MP2 |
| **RAM** | 1 GB LPDDR3 (typ.; 2 GB em modelos raros) |
| **eMMC** | 8 GB ou 16 GB (vendor varia) |
| **Video Out** | HDMI 1.4 (up to 4K @ 30 Hz) |
| **Audio** | HDMI, S/PDIF, 3.5mm jack (modelo-dependente) |
| **Networking** | 100 Mbps Ethernet (não Gigabit) |
| **Wireless** | Wi-Fi (esp8089 ou RTL8189; device-dependente) |
| **USB** | 2× USB-A (Host), 1× Micro-USB (OTG) |

### Partition Layout (Rockchip RK3229)

| Partition | Offset | Size | Contents |
|-----------|--------|------|----------|
| loader1 (idbloader) | 0x40 | 496 sectors | SPL (RC4-obfuscado) |
| loader2 (u-boot.itb) | 0x200 | 1024 sectors | U-Boot + ATF |
| trust | 0x600 | 128 sectors | OP-TEE TEE (ou vazio) |
| misc | 0x680 | 128 sectors | Recovery flags |
| boot | 0x700 | 32768 sectors | Kernel + ramdisk |
| root | 0x8700 | Resto | Rootfs (Android /system) |

**Nota**: Armbian re-partitions eMMC com apenas boot + root. Acima é Android layout (pré-wipe).

### GPIO Pinout (D+ header de debug, se existir)

| Pin | Sinal | Voltage |
|-----|-------|---------|
| 1 | GND | - |
| 2 | TX | 3.3V |
| 3 | RX | 3.3V |
| 4 | NC | - |

Não é padrão; varie conforme revisão PCB.

### Community Resources

- **Rockchip RK3229 Wiki**: https://opensource.rock-chips.com/wiki_RK3229
- **Armbian RK322x**: https://www.armbian.com/rk322x/
- **MattWestb R29 Teardown** (GitHub): https://github.com/MattWestb/R29-MXQ-LP3-V2.3-00908
- **CNX Software Teardown** (2016): https://www.cnx-software.com/2016/03/07/mxq-4k-rockchip-rk3229-android-tv-box-unboxing-and-teardown/
- **XDA Forums / FreakTab**: RK3229 device trees e firmware archives

---

## Apêndice B: Supply Chain Security Context

### BadBox 2.0 (FBI PSA250605)

| Fator | Detalhe |
|-------|---------|
| **Escala** | 10M+ devices afetados (lawsuit da Google vs. ator de ameaça, Jul 2025) |
| **Malware Base** | Triada (Android, multi-year history) |
| **Vetor de infecção #1** | **Pre-flash na fábrica** — malware já instalado antes de você comprar |
| **Vetor de infecção #2** | First-boot OTA — device contacta servidor malicioso durante setup Android inicial |
| **Vetor de infecção #3** | Sideload via app store não-oficial |
| **Dispositivos afetados** | Android TV streaming boxes, digital projectors, vehicle infotainment, digital frames |
| **IoC domains (HUMAN)** | `catmore88[.]com`, `ycxrl[.]com`, `duoduodev[.]com`, `flyermobi[.]com`, `motiyu[.]net`, `qazwsxedc[.]xyz` (109 total) |

**Por que é crítico para você**: TV boxes RK3229 genéricas (aqui, MXQ Pro 4K) são especificamente nomeadas em BadBox coverage. Sua caixa é praticamente segura que foi comprometida na fábrica.

**Mitigation via OpenBox**: 
- Wipe completo antes de qualquer conectividade de rede
- Flash via maskrom (contorna software pré-infectado)
- Nenhuma primeira-execução automática
- DNS sinkhole dos IoC domains via Pi-hole (defesa em profundidade)

---

### Vo1d Backdoor (Doctor Web, 2024-09)

| Fator | Detalhe |
|-------|---------|
| **Escala** | 1.3M Android TV boxes em 197 países |
| **Países mais afetados** | **Brasil #1**, Marrocos, Paquistão, Arábia Saudita, Argentina, Rússia, Tunísia |
| **Persistência** | `/system/bin/debuggerd` é renomeado; `/system/xbin/vo1d` + `/system/xbin/wd` colocados |
| **Trick de nome** | "vo1d" simula `vold` (substitui l por 1) para parecer Android legítimo |
| **Capacidade** | C2-driven download + execução de arbitrary software |

**Relevância direta**: Você (operador) está em Brasília; Brasil é #1 país infectado por Vo1d. Boxes do AliExpress/Shopee praticamente 100% contêm malware.

**Mitigação via OpenBox**: Vo1d persiste apenas na partition `/system` do Android. Wipe + Armbian flash remove completamente. Vo1d não infecta BootROM (silicon, imutável) ou U-Boot SPL (sobrescrito por Armbian).

---

### Honest Disclaimer — What You Can and Cannot Do

**O que OpenBox **NÃO** faz:**
- ❌ Impede acesso físico (se alguém abre a caixa e shorts maskrom pad, pode reflashar)
- ❌ Protege contra estado brasileiro (IMSI catchers, SIGINT)
- ❌ Oferece anonimato absoluto (correlação de tráfego ainda é possível)

**O que OpenBox **FAZ**:**
- ✅ Remove BadBox 2.0 e Vo1d completamente (wipe destrói `/system` partition)
- ✅ Encripta DNS queries (dnscrypt-proxy DoH/DoQ)
- ✅ Tunela tráfego de streaming via WireGuard (ISP não vê serviço que você acessa)
- ✅ Bloqueia rastreadores em nível de rede (Pi-hole)
- ✅ Auditável (código aberto, sem binary blobs no path crítico)

---

## Histórico de Revisões

| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0 | 2026-04-25 | Versão inicial: 11 seções consolidadas de RK3229_THREAT_RESEARCH.md, CASE_STUDY.md, RUNBOOK.md |

---

**FIM DO GUIA**

Para questões, vide [docs/REFERENCES.md](./REFERENCES.md) para links comunitários.
