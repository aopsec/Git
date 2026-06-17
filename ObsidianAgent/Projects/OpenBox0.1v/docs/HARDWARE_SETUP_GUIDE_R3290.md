# Guia de Setup & Boot — R3290_V8.1 (Família rk322x)

> **Formatação e boot de TV box Android genérico para Armbian limpo**  
> Plataforma: R3290_V8.1 · Família SoC: Rockchip rk322x (RK3228A / RK3228B / RK3229)  
> Versão: 2.0 · Data: 2026-04-25

---

## § 1. O Que é o R3290_V8.1

### Identificação do device

**R3290_V8.1** é uma designação impressa na PCB pelo fabricante OEM chinês. Ela **não é o nome do SoC** — é o código do layout da placa de circuito impresso:

| Campo | Significado |
|-------|-------------|
| `R3290` | Código interno de produto do fabricante (OEM) |
| `V8.1` | Revisão 8.1 da PCB (iteração de hardware) |
| SoC real | **Desconhecido até abrir o device** — provavelmente RK3228A, RK3228B ou RK3229 |

A versão V8.1 é uma revisão de PCB **alta** (comparar: R29_5G_LP3 vai até V3.x). Isso sugere que o R3290 é um design de placa posterior, possivelmente de 2022–2025, produzido em grande escala em diversas iterações.

### Família rk322x — Por que isso importa

Rockchip agrupa RK3228A, RK3228B e RK3229 na família **rk322x**. A comunidade Armbian mantém uma única imagem (`rk322x-box`) que funciona com **todos os três SoCs**. Isso significa:

> Mesmo sem saber qual SoC exato está no R3290_V8.1, a imagem `rk322x-box` provavelmente funciona.

Confirmação é feita pós-boot com `cat /proc/device-tree/model`.

### Especificações esperadas da família rk322x

| Componente | Especificação Típica |
|-----------|---------------------|
| **SoC** | RK3228A / RK3228B / RK3229 |
| **CPU** | Quad-core ARM Cortex-A7 @ 1.0–1.5 GHz (32-bit) |
| **GPU** | Mali-400 MP2 |
| **RAM** | 512 MB a 2 GB DDR3 / LPDDR3 |
| **eMMC** | 8 GB, 16 GB ou 32 GB (vendor varia: NANYA, Foresee, Kingston, Samsung) |
| **Ethernet** | 100 Mbps (não Gigabit — limitação de hardware) |
| **Wi-Fi** | Integrado ou módulo externo (ESP8089, RTL8723BS, RTL8189FS) |
| **HDMI** | HDMI 1.4 (max 4K @ 30 Hz; na prática 1080p para streaming) |
| **USB** | 2× USB-A (Host) + 1× Micro-USB ou USB-C (OTG/Recovery) |

### Supply-chain: O device está comprometido de fábrica

**BadBox 2.0** (FBI IC3 PSA250605, 2025): 10 milhões+ de devices Android TV box infectados pré-compra. MXQ Pro 4K e designs similares baseados em rk322x estão explicitamente documentados em cobertura BadBox/Vo1d. Brasil é o país **#1 afetado** por Vo1d (Doctor Web, 2024).

**Regra crítica:** Nunca ligue este device em qualquer rede antes de wipar o Android. O vetor de infecção `first-boot OTA` é automático e silencioso.

---

## § 2. Três Métodos de Entrada em Maskrom Mode

O R3290_V8.1 é um SoC Rockchip. Todo Rockchip tem **Maskrom mode** gravado no silicon — não pode ser desabilitado por software. Existem 3 métodos para entrar nele:

### Método A — Botão de Reset (Mais Fácil, Sem Abrir)

A maioria dos TV boxes rk322x tem um **botão de reset escondido** dentro do buraco da porta AV ou em pequeno orifício na parte de baixo/lateral da caixa.

```
Procedimento:
  1. Inserir clipe de papel ou palito fino no buraco AV (ou orifício de reset)
  2. MANTER pressionado o botão de reset
  3. Enquanto mantém pressionado: plugar cabo USB-OTG no PC
  4. Enquanto mantém pressionado: conectar fonte 5V (ligar o device)
  5. Aguardar 3–5 segundos com botão pressionado
  6. SOLTAR o botão

Verificar no PC:
  sudo rkdeveloptool ld
  # Expected: DevNo=1  Vid=0x2207,Pid=0x330c,...  Loader
  # (Loader mode — aceita flash de firmware Android)
  
  # Para Maskrom mode (flash completo), full erase o eMMC primeiro:
  sudo rkdeveloptool ef
  # Então desligar e repetir Método A — device entrará em Maskrom
  # Expected: DevNo=1  Vid=0x2207,Pid=0x320c,...  Maskrom
```

**Quando usar**: Primeira tentativa. Device com Android ainda funcional ou semi-funcional.

---

### Método B — Short do CLK do eMMC (Maskrom Direto)

Abre o device e curto-circuita o pino CLK do eMMC para GND. O BootROM não encontra clock no eMMC e entra em Maskrom automaticamente.

**Por que "CLK" e não o pad genérico**: No rk322x, o BootROM tenta ler o bootloader do eMMC. Se o clock do eMMC estiver short para GND, o eMMC não responde, e o BootROM cai para Maskrom.

```
Equipamento necessário:
  - Multímetro (modo continuidade / resistência)
  - Agulha ou fio fino (para o short)
  - Câmera/lupa (para ver o eMMC chip pequeno)
```

**Localizar o chip eMMC e o pino CLK:**

```
Padrão JEDEC eMMC — pinagem BGA (Ball Grid Array):
O eMMC é um chip retangular preto, tipicamente 11.5mm × 13mm.
Não tem pinos visíveis (BGA = balls embaixo).

Para rk322x, o CLK test point está geralmente:
  1. Como via de teste PRÓXIMA ao chip eMMC (lado da PCB visível)
  2. Silkscreen pode estar rotulado: "CLK", "NAND_CLK", "EMMC_CLK", "TP_CLK"
  3. Ou pode NÃO ter rótulo — use multímetro para identificar
```

**Identificar o pino CLK por continuidade:**

```
Passos com multímetro:
  1. Multímetro em modo continuidade (buzzer)
  2. Uma ponta em qualquer GND da PCB (conector USB, capacitor, chassi)
  3. Outra ponta em cada via próxima ao eMMC
  4. O pino CLK NÃO toca GND em repouso (sem beep)
  5. Quando shorted manualmente (próxima etapa), deve fazer o device entrar em maskrom

Método alternativo (resistência):
  1. DEVICE DESLIGADO
  2. Teste resistência entre via suspeita e GND
  3. CLK tipicamente: 10–100 kOhm (pull-up resistor para VCC)
  4. GND: 0 Ohm
  5. VCC power: também alto, mas cuidado — não é CLK
```

**Short do CLK para entrar em Maskrom:**

```
Sequência:
  1. Conectar cabo USB-OTG no PC (não conectar fonte ainda)
  2. Abrir terminal: sudo rkdeveloptool ld (aguardar pendente)
  3. SHORT o pino CLK para GND com agulha/fio (MANTER SHORTED)
  4. Conectar fonte 5V ao device (ligar)
  5. Aguardar 2–3 segundos
  6. SOLTAR o short

Se correto, rkdeveloptool ld mostrará:
  DevNo=1  Vid=0x2207,Pid=0x320c,LocationID=XXX  Maskrom
```

**Quando usar**: Device com Android corrompido ou pós-erase parcial.

---

### Método C — Short de Pinos NAND (Apenas para eMMC tipo TSOP)

Alguns modelos rk322x mais antigos usam armazenamento NAND em formato TSOP48 (pinos visíveis) em vez de eMMC BGA. Neste caso:

```
Localizar chip NAND:
  - Package retangular com pinos metálicos visíveis nas laterais (48 pinos total)
  - Diferente do eMMC BGA que não tem pinos visíveis

Short dos pinos NAND:
  - Pinos 6–7 OU 7–8 contando da parte inferior direita do chip
  - Enquanto short: conectar USB + ligar fonte
  - Device entra em Maskrom

Referência técnica (Ugoos):
  "Short the 6th-7th or 7th-8th pin from NAND bottom on right side"
```

**Quando usar**: Se o chip de armazenamento tem pinos visíveis (TSOP48), não BGA.

---

## § 3. Preparação da Máquina Dev

### Instalar rkdeveloptool

```bash
# Ubuntu / Debian:
sudo apt update
sudo apt install -y build-essential libusb-1.0-0-dev libudev-dev git

# De source (recomendado — versão mais recente):
git clone https://github.com/rockchip-linux/rkdeveloptool.git
cd rkdeveloptool
autoreconf -i
./configure
make -j$(nproc)
sudo make install
sudo ldconfig

# Verificar instalação:
rkdeveloptool --version
# Expected: rkdeveloptool ver 1.32 (ou similar)

# Configurar udev (evitar sudo para cada comando):
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="2207", MODE="0666", GROUP="plugdev"' \
  | sudo tee /etc/udev/rules.d/99-rockchip.rules
sudo udevadm control --reload-rules
sudo usermod -a -G plugdev $USER
# (fazer logout/login para aplicar grupo)

# macOS (via Homebrew):
brew install libusb automake
git clone https://github.com/rockchip-linux/rkdeveloptool.git
cd rkdeveloptool && autoreconf -i && ./configure && make && sudo make install
```

### Baixar Imagem Armbian para rk322x

```bash
# Diretório Armbian para rk322x-box:
# https://www.armbian.com/rk322x-tv-box/
# ou
# https://forum.armbian.com/topic/34923-csc-armbian-for-rk322x-tv-box-boards/

# Download da imagem estável mais recente:
cd /tmp
wget "https://dl.armbian.com/rk322x-tv-box/Bookworm_current"
# ou navegar para a URL e baixar .img.xz diretamente

# Verificar checksum (SHA256 disponível na página de download):
sha256sum Armbian_*_rk322x-tv-box_*.img.xz
# Comparar com hash na página — devem ser idênticos

# Extrair:
xz -dk Armbian_*_rk322x-tv-box_*.img.xz
# Resultado: arquivo .img (~2–4 GB)

ls -lh Armbian_*_rk322x-tv-box_*.img
# Expected: 2.0G ou maior
```

**Nota sobre variantes de imagem rk322x**: A comunidade Armbian mantém variantes para:
- DDR2 RAM (mais antigo, menos comum)
- DDR3 RAM (maioria dos devices modernos)
- eMCP (eMMC e DRAM num único chip — menos comum)

Se a imagem padrão não bootar, tente variante DDR2 ou eMCP.

### Checklist Pré-Flash

```
☐  rkdeveloptool instalado e funcionando (rkdeveloptool --version)
☐  libusb instalado
☐  Imagem Armbian rk322x baixada e checksum verificado
☐  Imagem extraída (.img, não .img.xz)
☐  Cabo USB-OTG funcional (testado com outro device)
☐  Método de maskrom entry identificado (A, B ou C — §2)
☐  Fonte 5V pronta
☐  Cabo Ethernet para primeiro boot
```

---

## § 4. Flash — Procedimento Completo

### 4.1 Entrar em Maskrom (escolha o método em §2)

```bash
# Verificar que device está em maskrom:
sudo rkdeveloptool ld

# Possíveis outputs:
# 1. Maskrom mode (desejado para flash limpo):
#    DevNo=1  Vid=0x2207,Pid=0x320c,...  Maskrom
#
# 2. Loader mode (Android ainda parcialmente funcional):
#    DevNo=1  Vid=0x2207,Pid=0x330c,...  Loader
#    → Faça erase para entrar em Maskrom:
#    sudo rkdeveloptool ef
#    → Repita entrada em Maskrom

# 3. Nenhum output (device não detectado):
#    → Volte para §2 e revise o método
```

### 4.2 Flash da Imagem Armbian

**ADVERTÊNCIA CRÍTICA**: Não interrompa o flash. Cabo desconectado durante escrita = eMMC corrompido (recovery requer repetir maskrom + erase + reflash).

```bash
# Verificar imagem antes de iniciar:
ls -lh /tmp/Armbian_*_rk322x-tv-box_*.img
# Expected: arquivo com ~2+ GB

# Iniciar flash (substitua pelo nome exato do arquivo):
sudo rkdeveloptool wl 0 /tmp/Armbian_24.02_rk322x-tv-box_bookworm_current.img

# Output esperado (leva 5–20 minutos para eMMC 8–16 GB):
# Writing data...
# Write LBA 0 [=>                                                  ]   3%
# Write LBA 0 [=========>                                          ]  19%
# ...
# Write LBA 0 [==================================================>] 100%  3m27s
# Write success

# Reboot o device:
sudo rkdeveloptool rd
# Device desaparece de rkdeveloptool ld (sai de maskrom, vai bootar)
```

### 4.3 Confirmar SoC pós-boot (obrigatório)

```bash
# Após Armbian bootar (~60–90 segundos):
# Conectar Ethernet, descobrir IP via router ou arp-scan
arp-scan --localnet | grep -i rockchip

# SSH:
ssh root@<IP>   # senha padrão: 1234 (Armbian pede mudança no primeiro login)

# Confirmar SoC:
cat /proc/device-tree/model
# Esperado: "rockchip,rk3229-..." OU "rockchip,rk3228a-..." OU similar rk322x

# Confirmar arquitetura:
uname -m
# Expected: armv7l (32-bit — correto para rk322x)

dpkg --print-architecture
# Expected: armhf
```

Se o output de `/proc/device-tree/model` contiver `rk3228`, `rk3229`, ou `rk322x` — confirmado. A imagem `rk322x-box` é compatível com seu device.

---

## § 5. Primeiro Boot & Phase 0 Verification

### Sinais de Boot Saudável

```
Sequência esperada (60–120 segundos):
  - LED acende (atividade)
  - HDMI: logo Armbian ou texto de kernel boot
  - Ethernet inicia (procura DHCP)
  - Login prompt aparece (tty1 ou via SSH)
  - Armbian solicita nova senha de root no primeiro login
```

### Executar Phase 0 Fingerprint

Após login, execute o script de captura de hardware:

```bash
# No device (via SSH ou tty):
cd /path/to/openbox-repo
sudo bash tools/fingerprint-rk3229.sh > docs/hw/r3290_v8.1.txt 2>&1

# Examinar resultado:
cat docs/hw/r3290_v8.1.txt
```

### Phase 0 Gate Criteria — 4 Checks Obrigatórios

**Check 1 — SoC correto:**

```bash
cat /proc/device-tree/model
# PASS: contém "rk3228", "rk3229", ou "rk322x"
# FAIL: outro SoC → imagem errada flashed
```

**Check 2 — Arquitetura 32-bit armhf:**

```bash
uname -m && dpkg --print-architecture
# PASS: armv7l / armhf
# FAIL: aarch64 / arm64 → imagem 64-bit errada
```

**Check 3 — WireGuard kernel module:**

```bash
modinfo wireguard
# PASS: output com "filename:", "version:", "description:"
# FAIL: "ERROR: Module wireguard not found"
# Solução: apt install -y wireguard linux-modules-extra-$(uname -r)
```

**Check 4 — Watchdog device:**

```bash
ls /dev/watchdog*
# PASS: /dev/watchdog0 (ou outros)
# FAIL: "No such file or directory"
# Solução: modprobe dw_wdt && ls /dev/watchdog*
```

Se **qualquer** check falhar → não prosseguir. Identificar causa, corrigir, retry.

---

## § 6. Verificação de Segurança Pós-Flash

Execute estes 6 checks **antes de conectar à rede de produção**. Confirmam que o Android — com BadBox 2.0 e Vo1d — foi completamente removido.

```bash
# ─────────────────────────────────────────────────────
# CHECK 1: Nenhuma partição Android sobreviveu
# ─────────────────────────────────────────────────────
sudo lsblk -o NAME,LABEL,FSTYPE | \
  grep -Ei 'system|vendor|recovery|misc|frp|oem|trust'
# PASS: sem output (apenas mmcblk0p1/p2 de Armbian)
# FAIL: qualquer match → flash incompleto, refazer

# ─────────────────────────────────────────────────────
# CHECK 2: Vo1d não substituiu debuggerd
# ─────────────────────────────────────────────────────
[[ -e /system/bin/debuggerd ]] \
  && echo "FAIL: /system presente (inesperado em Armbian)" \
  || echo "PASS: sem /system"

# ─────────────────────────────────────────────────────
# CHECK 3: Nenhum tráfego C2 BadBox ativo
# ─────────────────────────────────────────────────────
ss -tnp 2>/dev/null | \
  grep -Ei 'catmore88|ycxrl|duoduodev|flyermobi|motiyu|qazwsxedc'
# PASS: sem output
# FAIL: qualquer match → device não foi completamente limpo

# ─────────────────────────────────────────────────────
# CHECK 4: Captura de baseline de rede (60s)
# ─────────────────────────────────────────────────────
IFACE=$(ip route show default | awk '{print $5; exit}')
sudo timeout 60 tcpdump -nn -i "$IFACE" -c 200 \
  not arp and not stp and not 'udp port 5353' \
  -w /tmp/baseline.pcap 2>/tmp/baseline.log
echo "Capturado $(wc -c < /tmp/baseline.pcap) bytes"
# Inspecionar:
tcpdump -r /tmp/baseline.pcap -n 2>/dev/null | head -30
# Esperado: apenas gateway, DNS, NTP
# Suspeito: IPs desconhecidos ou domínios não reconhecidos

# ─────────────────────────────────────────────────────
# CHECK 5: Armbian release válida
# ─────────────────────────────────────────────────────
cat /etc/armbian-release | grep -E '^(BOARD|BUILD_DATE|VERSION)'
# PASS: BOARD=rk322x-tv-box (ou variante rk322x)
# FAIL: BOARD diferente → imagem errada

# ─────────────────────────────────────────────────────
# CHECK 6: Nenhum kernel module suspeito
# ─────────────────────────────────────────────────────
find /lib/modules/$(uname -r) -name '*.ko*' | \
  xargs -I{} basename {} .ko | sort -u | \
  grep -Eiv '^(rockchip|rk_|sun[0-9]+|brcm|rtl|mt[0-9]+|ath|cfg80211|mac80211|usb|nft|ip|sch|cls|wireguard|cake|fou|ipt|xt|nf|crypto|aes|sha|gcm|chacha|poly|ext4|fat|vfat|nls_|usbcore|hid|input|drm|gpu|i2c|spi|uart|tty|serial|loop|md|raid|btrfs|f2fs|squashfs|fuse|nfs|cifs|isofs|cdrom|sd|mmc|scsi|sr|dm|tun|tap|veth|bridge|vxlan|gre|geneve|bonding|8021q|gpio|pwm|leds|hwmon|thermal|cpufreq|cpuidle|power|reboot|rtc|wd|watchdog|snd|sound|video|media|v4l|uvc|alsa|sof|fb|backlight|panel|hdmi|dp|mipi|dsi|csi|vpu|rga|iep|vdec|venc|jpeg|h264|h265|vp8|vp9|av1)$' \
  && echo "WARN: módulos suspeitos encontrados" || echo "PASS: apenas módulos conhecidos"
```

---

## § 7. Próximos Passos — Instalar OpenBox

Com todos os 6 checks passando:

```bash
# 1. Atualizar pacotes (opcional mas recomendado):
sudo apt update && sudo apt upgrade -y

# 2. Clonar repositório OpenBox (se não já feito):
cd /root
git clone <URL-do-repo-openbox>
cd openbox

# 3. Dry-run:
sudo bash install.sh --dry-run

# 4. Instalar (30–45 minutos):
sudo bash install.sh
```

Referências:
- `docs/CASE_STUDY.md` — visão de arquitetura
- `docs/THREAT_MODEL.md` — escopo de proteção
- `docs/HARDENING_PLAN_v2.md` — implementação detalhada
- `docs/RUNBOOK.md` — operações e troubleshooting

---

## § 8. Troubleshooting

### `rkdeveloptool ld` não detecta o device

```
Diagnóstico sequencial:

1. Cabo USB-OTG:
   lsusb | grep 2207
   # Se nada: cabo ou permissão, NÃO o método de maskrom
   # Se vid=2207 aparece: method funcionou, problema em outro lugar

2. Permissões:
   sudo rkdeveloptool ld    # sempre tente com sudo primeiro
   
3. Porta USB:
   - Tente porta diferente no PC
   - Evite hubs USB (usar porta direta na máquina)
   - Tente cabos diferentes (cabos power-only são comuns)

4. Driver / kernel:
   sudo dmesg | tail -20
   # Procure por: "new high-speed USB device" e "2207"
   # Se "idVendor=2207, idProduct=0006": Device em modo LOADER (não maskrom)
   # Se "idVendor=2207, idProduct=0006" e NÃO entra em flash: use erase primeiro

5. Método de maskrom errado:
   - Tente todos os 3 métodos (§2) sistematicamente
   - Método A (botão) falha? → Tente B (CLK short)
   - Tente diferentes tempos: short mais longo (10s), short mais curto (1s)
```

### Flash falha no meio (`Transfer Error`, `Write timeout`)

```bash
# Recovery:
# 1. Re-enter maskrom (§2)
# 2. Erase completo:
sudo rkdeveloptool ef
# (leva 3–8 minutos para eMMC de 8–16 GB)

# 3. Retry flash:
sudo rkdeveloptool wl 0 /tmp/Armbian_*.img

# Causas comuns de falha:
# - Cabo USB instável → use porta direta, não hub
# - Fonte 5V insuficiente → verifique que device não reinicia durante flash
# - Imagem corrompida → verificar sha256sum
```

### Boot falha / tela preta

```bash
# Diagnóstico 1: Verificar se eMMC foi escrito
# Re-enter maskrom, então:
sudo rkdeveloptool rd 0x0 512 /tmp/check.bin
xxd /tmp/check.bin | head -4
# Se output é zeros (0x00000000): flash não foi gravado → retry
# Se output tem dados: flash OK, problema é outro

# Diagnóstico 2: Imagem errada
# A imagem rk322x-box pode não suportar sua variante específica
# Tentar imagens alternativas:
#   - rk322x DDR2 variant (se device tem DDR2 RAM — menos comum)
#   - rk322x eMCP variant (se tem chip combinado eMMC+RAM)
#   - LibreELEC para rk3228/rk3229 (alternativa mais leve)

# Diagnóstico 3: Serial console (ver § 9)
# É o método mais confiável para ver o que está acontecendo durante boot
```

### Device não tem botão de reset visível (Método A)

```
Alguns modelos mais novos não têm buraco AV (saída A/V foi removida).
Neste caso:
  1. Use Método B (CLK short) — mais confiável para V8.x
  2. Abrir o device é necessário
  3. Verificar se há orifício de reset na lateral/fundo (nem sempre é no AV)
  4. Verificar se há botão físico na PCB marcado "RESET" ou "REC"
```

### Armbian não detecta rede (sem IP DHCP)

```bash
# Verificar interface de rede:
ip link show
# Esperado: eth0 ou enp1s0 (Rockchip Ethernet)

# Forçar DHCP:
sudo dhclient -v eth0

# Se "eth0: error fetching interface information":
# Driver Ethernet não carregou
lsmod | grep -i dwmac
# Driver Rockchip Ethernet: stmmac ou dwmac-rk
# Se ausente: apt install linux-modules-extra-$(uname -r)

# Wi-Fi como alternativa (se módulo presente):
iw dev    # lista interfaces Wi-Fi
wpa_passphrase "SSID" "senha" > /etc/wpa_supplicant/wpa_supplicant.conf
wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
dhclient wlan0
```

---

## § 9. Serial Console (Debug Avançado)

O serial console é a ferramenta definitiva para diagnosticar problemas de boot que não aparecem em HDMI.

### Hardware necessário

- Adaptador USB-Serial: CH340G, CP2102, PL2303, ou FT232 (evite clones — timing sensível)
- 3 jumpers fêmea-fêmea
- **Tensão: 3.3V APENAS** — 5V queima o SoC Rockchip

### Localizar header serial na PCB

A maioria das PCBs rk322x tem um header de 3 a 4 pinos não populado ou com jumpers próximos ao edge da PCB. Procure:

```
Silkscreen comum: "UART0", "DEBUG", "J1", "CON1", "3V3/TX/RX/GND"

Layout mais comum:
  ┌─────┐
  │ VCC │  ← 3.3V (NÃO conectar — não necessário se USB-serial tem 3.3V)
  │ GND │  ← Conectar a GND do adaptador USB-serial
  │ TX  │  ← Conectar ao RX do adaptador (CRUZADO)
  │ RX  │  ← Conectar ao TX do adaptador (CRUZADO)
  └─────┘

TX/RX são sempre cruzados (TX de um vai no RX do outro)
```

### Conectar e monitorar

```bash
# Identificar device serial:
ls /dev/ttyUSB* /dev/ttyACM*

# Abrir serial console (115200 baud, 8N1):
minicom -D /dev/ttyUSB0 -b 115200
# ou:
picocom -b 115200 /dev/ttyUSB0
# ou (mais simples):
screen /dev/ttyUSB0 115200

# Ligar o TV box
# Output esperado (primeiros 2 segundos de boot):
# DDR3, 792MHz
# In:    serial
# Out:   serial
# Err:   serial
# Model: Rockchip RK3229
# ...kernel boot messages...
```

### O que procurar no serial output

| Mensagem | Significado |
|----------|-------------|
| `rockchip,rk3229` | SoC identificado (PASS) |
| `rockchip,rk3228a` | SoC identificado alternativo (PASS) |
| `EXT4-fs (mmcblk0p2)` | Rootfs montado (PASS — Armbian rodando) |
| `Kernel panic` | Imagem incompatível com hardware |
| `MMC: no card present` | eMMC não detectado (flash falhou) |
| `could not load 'rockchip/rk3229-box.dtb'` | Device tree incorreto para sua PCB |

Se `rockchip/rk322x-tvbox.dtb` ou similar for mencionado em erro — pode ser necessário selecionar DTB diferente no Armbian.

---

## Apêndice A: Especificações Técnicas rk322x

### Comparação SoC da Família

| Especificação | RK3228A | RK3228B | RK3229 |
|--------------|---------|---------|--------|
| **CPU** | Cortex-A7 quad @ 1.2 GHz | Cortex-A7 quad @ 1.2 GHz | Cortex-A7 quad @ 1.5 GHz |
| **GPU** | Mali-400 MP2 | Mali-400 MP2 | Mali-400 MP2 |
| **VPU** | 4K H.265/H.264 | 4K H.265/H.264 | 4K H.265/H.264 |
| **DRAM** | DDR3/LPDDR2 | DDR3/DDR2 | LPDDR3/DDR3 |
| **eMMC** | eMMC 4.51 | eMMC 4.51 | eMMC 5.0 |
| **Ethernet** | 10/100 Mbps | 10/100 Mbps | 10/100 Mbps |
| **USB OTG** | USB 2.0 OTG | USB 2.0 OTG | USB 2.0 OTG |
| **Processo** | 28nm | 28nm | 28nm |

### Layout de Partição Rockchip (Android — pré-wipe)

| Partição | Setor | Conteúdo | Wipe? |
|----------|-------|----------|-------|
| loader1 | 0x40 | idbloader (SPL) | ✅ Sim |
| loader2 | 0x200 | U-Boot | ✅ Sim |
| trust | 0x600 | OP-TEE | ✅ Sim |
| misc | 0x680 | Flags recovery | ✅ Sim |
| boot | 0x700 | Kernel Android | ✅ Sim |
| recovery | 0x2700 | Recovery Android | ✅ Sim |
| system | 0x8700 | Android OS (**Vo1d vive aqui**) | ✅ Sim |
| userdata | — | Dados apps | ✅ Sim |
| **BootROM** | silicon | Maskrom mode | ❌ Imutável |

Após flash Armbian: apenas `boot` (p1) e `rootfs` (p2) existem.

---

## Apêndice B: BadBox 2.0 & Vo1d — Contexto de Ameaça

### Por Que Wipar Antes de Qualquer Rede

**BadBox 2.0** (FBI IC3 PSA250605, junho 2025):
- 10 milhões+ de devices comprometidos
- 3 vetores: (1) **pré-flash na fábrica**, (2) first-boot OTA, (3) sideload
- Sua caixa R3290_V8.1 está **muito provavelmente pré-infectada de fábrica**
- Não há sinal externo visível de infecção

**Vo1d** (Doctor Web, setembro 2024):
- 1.3 milhões de Android TV boxes em 197 países
- **Brasil = País #1 infectado** (seguido de Marrocos, Paquistão)
- Mecanismo: substitui `/system/bin/debuggerd` + coloca `/system/xbin/vo1d`
- Nome mimetiza `vold` Android legítimo (substitui `l` por `1`)

**O que o wipe remove**: Vo1d e BadBox 2.0 vivem no Android `/system`, `/vendor` e partições de userdata. Flash completo via maskrom destrói e recria essas partições — malware removido completamente. O BootROM (maskrom) é imutável em silicon, mas é legítimo — não é malware.

### Domínios C2 Conhecidos (BadBox / Vo1d)

Para bloquear via Pi-hole pós-instalação:

```
catmore88.com
ycxrl.com          (e variantes de uma letra)
duoduodev.com
flyermobi.com
motiyu.net
qazwsxedc.xyz
```

Fonte: HUMAN Security Satori (109 domínios documentados; 5M+ subdomínios desativados em abril 2025).

---

## Apêndice C: Ferramentas e Referências

### Ferramentas Utilizadas

| Ferramenta | Uso | Link |
|-----------|-----|------|
| **rkdeveloptool** | Flash de firmware via USB (Linux/macOS) | [github.com/rockchip-linux/rkdeveloptool](https://github.com/rockchip-linux/rkdeveloptool) |
| **Armbian rk322x** | Imagem Armbian para rk322x-box | [armbian.com/rk322x-tv-box](https://www.armbian.com/rk322x-tv-box/) |
| **minicom** | Serial console (Linux) | `apt install minicom` |
| **picocom** | Serial console alternativo | `apt install picocom` |
| **RKDevTool** | Flash GUI para Windows (proprietário) | Rockchip Developer Portal |

### Comunidade & Fóruns

| Recurso | URL | Para quê |
|---------|-----|---------|
| **Armbian Forum rk322x** | [forum.armbian.com/topic/34923](https://forum.armbian.com/topic/34923-csc-armbian-for-rk322x-tv-box-boards/) | Suporte oficial Armbian para rk322x |
| **Armbian Rockchip CPU Boxes** | [forum.armbian.com/forum/193](https://forum.armbian.com/forum/193-rockchip-cpu-boxes/) | Fórum geral Rockchip TV boxes |
| **LibreELEC rk3228/rk3229** | [forum.libreelec.tv/thread/29006](https://forum.libreelec.tv/thread/29006-unofficial-le12-rk3228-rk3229-box-libreelec-builds/) | Builds LibreELEC alternativos |
| **MattWestb R29 teardown** | [github.com/MattWestb/R29-MXQ-LP3-V2.3-00908](https://github.com/MattWestb/R29-MXQ-LP3-V2.3-00908) | Teardown técnico rk322x (RK3228A) |
| **Gough's Tech Zone H96 V8** | [goughlui.com (H96 Mini V8)](https://goughlui.com/2021/01/09/teardown-h96-mini-v8-rk3228a-216gb-4k-ultra-hd-android-10-tv-box/) | Teardown RK3228A (PCB RK3228A-V30) |
| **Rockchip Open Source** | [opensource.rock-chips.com](https://opensource.rock-chips.com) | Docs técnicos oficiais Rockchip |

---

## Histórico de Revisões

| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0 | 2026-04-25 | Versão especulativa inicial (framework genérico) |
| 2.0 | 2026-04-25 | Reescrita completa com pesquisa: R3290_V8.1 = OEM PCB na família rk322x; 3 métodos de maskrom documentados; Armbian rk322x-box confirmado; Checklist de verificação pós-flash completo |

---

**NOTA FINAL**

Este guia assume R3290_V8.1 como um device da família rk322x (RK3228A/RK3228B/RK3229). Esta hipótese é suportada por:
1. "R29xx" é designação OEM comum para rk322x boards
2. A imagem Armbian `rk322x-box` cobre RK3228A, RK3228B e RK3229 num único build
3. Os PCB V71 e V8.x têm sido observados com SoCs desta família

Se `/proc/device-tree/model` pós-boot mostrar um SoC **diferente** de rk322x, consulte `docs/HARDWARE_SETUP_GUIDE.md` (RK3229 dedicado) ou a comunidade Armbian com o model string exato.
