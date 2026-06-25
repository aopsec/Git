# AVAL01-IC

Entrega da **Avaliação 01 — Projeto Técnico** da disciplina
**Introdução à Computação** (UniCEUB · Ciência da Computação).

| Campo | Valor |
|---|---|
| Instituição | Centro Universitário de Brasília — UniCEUB |
| Curso | Bacharelado em Ciência da Computação |
| Disciplina | Introdução à Computação |
| Tutor | Fabrício Ofugi |
| Autor | Alcides Olivo Pollazzon Soterio |
| Avaliação | AV01 — Projeto Técnico (item 03 da rubrica) |
| Data | 2026-04-28 |

## Arquivos

| Arquivo | Descrição |
|---|---|
| `AVAL01-IC.html` | Fonte canônica (PT-BR, print-CSS A4) |
| `AVAL01-IC.pdf`  | Renderização via Chromium headless |
| `AVAL01-IC.docx` | Conversão via Pandoc |
| `build.sh`       | Pipeline html → pdf + docx |
| `assets/`        | Dados de pesquisa (sources.json), infográficos extras |

## Como reproduzir

```bash
cd /home/aops/ObsidianAgent/Projects/IC01-aops/AVAL01-IC
bash build.sh
```

Dependências: `chromium` ou `msedge`/`msedge.exe` (obrigatório), `pandoc` (opcional para DOCX —
`sudo pacman -S pandoc-cli`).

No Windows + WSL, o script também tenta localizar `msedge.exe` em:
- `/mnt/c/Program Files (x86)/Microsoft/Edge/Application`
- `/mnt/c/Program Files/Microsoft/Edge/Application`

## Mapa rubrica AV01 → seção do documento

| Critério (rubrica oficial) | Seção | Evidência |
|---|---|---|
| Estudo de Caso — diagnóstico de cenário real | §2 + §4 | Contexto residencial BR + estudo de caso MXQ Pro 4k com fontes governamentais |
| Demanda de hardware/software/redes/APIs/IA | §6 + §7 | Demandas TI mapeadas ao alvo + diagramas de arquitetura |
| Qualidade Técnica — arquitetura justificada | §3, §5, §7 | Timeline, ADV7Sec/IPS-IDS, diagramas de blocos |
| Uso de Ferramentas — links externos exemplares | §10 | Repositórios GitHub (OpenBox, ADV7Sec) + apêndice de evidências |
| Estrutura do PDF — diagramas e escrita técnica | §3.1, §7.1, §7.3 | Infográfico de timeline + diagramas SVG inline |

## Estrutura do documento (10 seções + capa + sumário)

1. Resumo Executivo
2. Contexto e Justificativa
3. Timeline Completa do Projeto (infográfico + logs/reports/tests)
4. Estudo de Caso: Segurança do MXQ Pro 4k
5. ADV7Sec (IPS-IDS) — Mitigação Host-side
6. Demandas de Infraestrutura de TI
7. Arquitetura Proposta (diagramas SVG)
8. Conclusão e Direcionamento de Carreira
9. Referências
10. Apêndice: Evidências de Desenvolvimento

## Fontes técnicas reaproveitadas (este repo / IC01-aops)

- `OpenBox0.1v/CHANGELOG.md`, `install.d/*.sh`, `tests/*.sh` — timeline e testes
- `OpenBox0.1v/docs/security/RK3229_THREAT_RESEARCH.md` — análise de hardware
- `IPS_IDS/ADV7Sec_1.0v.py` + `adv7sec_1_0/` — base do §5
- `OpenBox0.1v/ADV7Box/ADV7Box.html` — referência de estilo (intacto)

## Fontes externas primárias

- `[IC]AV01-A.pdf` — modelo da rubrica oficial UniCEUB
- `compass_artifact_wf-562a9f40-...md` — análise técnica MXQ Pro / BadBox 2.0
- Anatel, MJSP/PF (Operação 404), MCom, Procon-SP, IBGE/CETIC.br — dados BR
- FBI PSA I-060525-PSA (jun/2025), HUMAN Security Satori, Dr.Web

## Pendências / TODOs (revisão antes da entrega final)

- (preenchido durante a redação como `<!-- TODO(autor): ... -->` no HTML)
