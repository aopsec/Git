# ADV7Box

<!-- [FIX-PTBR-01] Correções pontuais de norma culta no índice e nas referências do deliverable. -->

Documento técnico consolidado da entrega **AV01-A** (CEUB, 2026-04).
Une os dois pilares do projeto em um único artefato:

- **Pilar A — OpenBox v0.1** (`Projects/OpenBox0.1v/`) — caixa de borda RPi 4 com
  WireGuard full-tunnel, DNS cifrado, Pi-hole, Tor para metadados, nftables
  atomic kill switch e monitoramento local.
- **Pilar B — ADV7Sec** (`Projects/IPS_IDS/`, arquivo single-file `ADV7Sec.py`) —
  baseline IPS/IDS detection-only para workstation Arch (kernel ≥ 6.8, BTF):
  auditd, Falco modern-eBPF, Kunai, Suricata IDS-only, Zeek, Unbound dnstap,
  AIDE com pacman hook, ClamAV OnAccess escopado, Loki-RS/YARA, Lynis,
  chkrootkit, unhide, arch-audit.

## Arquivos nesta pasta

| Arquivo | Descrição |
|---|---|
| `ADV7Box.html` | Artefato primário, 20 seções, SVG + ASCII art, print-CSS A4 |
| `ADV7Box.pdf`  | Renderização do HTML via `chromium --headless --print-to-pdf` (29 páginas A4) |
| `README.md`    | Este índice |

## Como reproduzir o PDF

```bash
cd Projects/ADV7Box
chromium --headless=new --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=10000 \
  --print-to-pdf=./ADV7Box.pdf \
  ./ADV7Box.html
```

## Mapa da rubrica AV01-A → seção do documento

| Critério (rubrica oficial) | Seção | Evidência |
|---|---|---|
| Qualidade Técnica — arquitetura robusta e justificada | §3, §4, §5, §12 | Diagramas + 12 ADRs + regression fences |
| Uso de Ferramentas — exemplar | §9, §11, §18 | CI syntax (75/0), VM harness, smoke 16/3/0, auditoria |
| Estrutura do PDF — diagramas + escrita técnica | §3 (SVG + ASCII), §4, §7 | Fig. 3.1 SVG blocos + Fig. 3.2/3.3 ASCII + Fig. 4.1 fluxo |

## Guias de Hardware & Boot (OpenBox v0.2.0)

### RK3229 (R29_5G_LP3) — Bem Documentado

**`Projects/OpenBox0.1v/docs/HARDWARE_SETUP_GUIDE.md`** — guia completo com 11 seções (português)
- Pré-requisitos, identificação PCB, procedures detalhadas, troubleshooting
- Contexto de ameaças (BadBox 2.0, Vo1d)
- Phase 0 fingerprint + 4 gate criteria

### R3290_V8.1 & Variantes Rockchip — Framework Adaptável

**`Projects/OpenBox0.1v/docs/HARDWARE_SETUP_GUIDE_R3290.md`** — guia adaptável para R3290 e similares (português)
- Framework universal para Rockchip (RK3288, RK3328, etc.)
- Procedimento Passo 0: Confirmar SoC exato (CRÍTICO)
- Troubleshooting específico para device pouco documentado
- Serial console debug setup
- Community resources para consolidar detalhes R3290-específicos

**Nota**: R3290_V8.1 não possui documentação oficial consolidada. Use este guia como framework adaptável e colabore
com a comunidade (Armbian forums, XDA, GitHub) para confirmar SoC, imagem Armbian correta, e pad de maskrom.

## Fontes canônicas consultadas

Todos os trechos reproduzem conteúdo versionado em:

- `Projects/OpenBox0.1v/{README,docs/*,deliverables/AV01_OpenBox_Audit_Report.ms,install.sh,install.d/*}`
- `Projects/IPS_IDS/{README,PHASE1_BUILD,PHASE2_TUNING,docs/*,docs/adr/*,install.sh,install.py,ADV7Sec.py,reports/*}`

O documento consolidado é **derivado**, não fonte — alterações de projeto devem
acontecer nos repositórios de origem, com regeneração subsequente deste PDF.
