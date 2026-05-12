# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Propósito

Entrega **AV01-A** (CEUB, 2026-04) consolidada em um único artefato técnico. Documento
**derivado**, não fonte: une os dois pilares versionados em outros repos do meta-vault
em uma narrativa única de 20 seções alinhada à rubrica oficial.

- **Pilar A — OpenBox v0.1** (`../OpenBox0.1v/`) — caixa de borda RPi 4 (WireGuard,
  DNS cifrado, Pi-hole, Tor, nftables kill switch, monitoramento).
- **Pilar B — ADV7Sec** (`../IPS_IDS/`, single-file `ADV7Sec.py`) — baseline IPS/IDS
  detection-only para workstation Arch (auditd, Falco, Kunai, Suricata, Zeek,
  Unbound dnstap, AIDE, ClamAV, Loki-RS/YARA, Lynis).

## Arquivos

| Arquivo | Papel |
|---|---|
| `ADV7Box.html` | **Fonte canônica** desta pasta (1367 linhas, 20 §, SVG + ASCII, print-CSS A4) |
| `ADV7Box.pdf`  | Renderização do HTML (29 páginas A4) — regenerável, não editar à mão |
| `README.md`    | Índice; também catalogado no meta-vault como `Project Overview - ADV7Box.md` |

## Comandos

Toda mudança de conteúdo acontece em `ADV7Box.html`; o PDF é regerado a partir dele.

```bash
# Regenerar PDF (rodar a partir desta pasta)
chromium --headless=new --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=10000 \
  --print-to-pdf=./ADV7Box.pdf \
  ./ADV7Box.html

# Após editar README.md, ressincronizar catálogo do meta-vault (rodar na raiz)
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --sync --repo ../..
```

## Regra de fluxo

O documento é **derivado**. Alterações de projeto pertencem aos repositórios de origem
(`../OpenBox0.1v/`, `../IPS_IDS/`); só depois regenere o conteúdo deste HTML para
refletir a nova realidade. Editar este HTML sem refletir mudança upstream cria
divergência silenciosa entre deliverable e código.

## Estrutura do HTML

Seções §1–§20 cobrem: caso de TI, visão de dois pilares, arquitetura, cada pilar,
infraestrutura, modelo de ameaça consolidado, fases de instalação, testes, logs,
relatórios, 12 ADRs, trade-offs, limitações, timeline, critérios de aceite, aderência
à rubrica, evidências, referências, conclusão. Figuras: §3 (SVG blocos + ASCII), §4
(fluxo). Print-CSS dimensionado para A4 — quebras de página são parte do design,
não acidente.

## Gotchas

- O HTML usa `--virtual-time-budget=10000` no chromium para garantir renderização de
  SVG/CSS antes do snapshot. Reduzir esse valor pode produzir PDF com figuras vazias.
- README.md desta pasta é consumido pelo `Project Overview` do meta-vault — mudanças
  no título/cabeçalho exigem `--sync` na raiz para o catálogo refletir.
- Esta pasta **não** tem `.aops-vault.toml` próprio: vive sob o contrato do meta-vault
  raiz, no catálogo `Project Overviews` (folder `Projects`).
