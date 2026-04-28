# CLAUDE.md

Guidance para Claude Code ao operar nesta pasta.

## Propósito

Entrega da **Avaliação 01 — Projeto Técnico** da disciplina **Introdução à Computação**
(UniCEUB · Ciência da Computação · Tutor Fabrício Ofugi · Autor Alcides Olivo
Pollazzon Soterio).

Documento **derivado** que reaproveita o ecossistema técnico existente em
`/home/aops/ObsidianAgent/Projects/IC01-aops/`:

- `OpenBox0.1v/` — caixa de borda RK3229 (versionada, fonte canônica de timeline e código)
- `OpenBox0.1v/ADV7Box/` — entrega anterior AV01-A (referência visual; **não editar**)
- `IPS_IDS/` — instalador ADV7Sec (fonte canônica para §5)

Modelo da rubrica: `/home/aops/Downloads/[IC]AV01-A.pdf`.
Fonte primária do estudo de caso: `/home/aops/Downloads/compass_artifact_wf-562a9f40-...md`.

## Arquivos

| Arquivo | Papel |
|---|---|
| `AVAL01-IC.html` | **Fonte canônica** (PT-BR, print-CSS A4) |
| `AVAL01-IC.pdf`  | Renderização via Chromium headless — regenerável |
| `AVAL01-IC.docx` | Conversão via Pandoc — regenerável |
| `README.md`      | Índice + mapa rubrica AV01 → seção |
| `build.sh`       | Pipeline `html → pdf, html → docx` (pandoc opcional) |
| `assets/`        | Infográficos e dados de pesquisa (sources.json) |

## Comandos

```bash
# Regenerar PDF + DOCX
bash build.sh

# Validar HTML
xmllint --noout --html AVAL01-IC.html

# Conferir hashes
sha256sum AVAL01-IC.{html,pdf,docx}

# Auditar links externos
grep -oE 'https?://[^"<> ]+' AVAL01-IC.html | sort -u | \
  while read u; do
    code=$(curl -s -o /dev/null -w '%{http_code}' -I -L --max-time 10 "$u")
    printf '%s  %s\n' "$code" "$u"
  done
```

## Regra de fluxo

Conteúdo técnico (timeline, instalador, ADV7Sec) vive nos repos upstream.
Esta pasta só consolida narrativa e referências — alterações de código vão
aos diretórios `OpenBox0.1v/`, `IPS_IDS/` etc., e este HTML é regerado para
refletir a nova realidade.

## Gotchas

- Pandoc não vem por padrão no Arch (`pacman -S pandoc-cli` para instalar).
  `build.sh` continua mesmo sem pandoc, apenas pulando a etapa DOCX com aviso.
- Usar `--virtual-time-budget=10000` no chromium garante render dos SVG inline.
- Esta pasta não tem `.aops-vault.toml`: vive fora do contrato vault do meta-repo.
- Toda citação numérica em §4.2 precisa de fonte rastreável em §9.
- Pasta de referência intacta: `OpenBox0.1v/ADV7Box/` (entrega AV01-A consolidada).
