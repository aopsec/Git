# CLAUDE.md — CalculadoraSite

Ferramenta CLI/TUI em Python para **precificar sites no mercado brasileiro (2026)**.
Coleta o escopo de um projeto via wizard (Textual) ou flags (Typer) e gera um
orcamento (PDF com papel timbrado **ADVAN7Tech**, JSON e TXT).

## Stack

- Python 3.11+; **Textual** (TUI) + **Rich** (render); **Typer** (CLI);
  **ReportLab** (PDF); **pydantic v2** + **PyYAML** (dados). Testes: pytest +
  Textual Pilot. Lint/type: ruff (line-length 120) + mypy --strict.

## Comandos

```bash
# rodar (a partir do diretorio do projeto)
python CalculadoraSite.py                    # TUI interativa
python CalculadoraSite.py listar             # slugs do catalogo
python CalculadoraSite.py calcular -t institucional_simples -p 5 -o pdf

# gate de qualidade
ruff check . && mypy calculadora_site && pytest
pytest tests/test_pricing.py::test_caso_canonico_simples -v   # teste isolado
```

## Arquitetura (separe sempre logica de UI)

- `calculadora_site/core/pricing.py` = **motor de calculo PURO** (sem I/O). E a
  fonte da verdade da formula. Recebe `ProjetoInput` + `Catalogo`, devolve `Orcamento`.
- `calculadora_site/config/precos.yaml` = **todas** as tabelas de preco/horas/
  multiplicadores. **NUNCA hardcodar preco no codigo** — toda alteracao vai aqui.
- `calculadora_site/core/{models,catalog}.py` = schema pydantic + carregamento/validacao.
- `calculadora_site/formatting.py` = formatadores pt-BR puros (modulo-folha; core e ui importam).
- `calculadora_site/ui/` = apresentacao (theme ADVAN7Tech, render Rich, app Textual).
- `calculadora_site/reports/` = exportacao (pdf/json/txt). `ui/theme.py` e a unica
  fonte de estilo (cores + marca), compartilhada por TUI e PDF.

Dependencias: `reports` e `ui` -> `core` -> `formatting`. Nunca o inverso
(core nao importa ui).

## Formula (resumo; detalhe no docstring de pricing.py)

```
horas_total  = (horas_base + paginas_extra*h/pag + Σ horas_features) * (1 + overhead%)
subtotal     = horas_total * valor_hora * mult_design + Σ add_ons_fixos
preco_final  = subtotal * (1+urgencia%) * (1+localizacao%) * (1+margem%) / (1 - tributo%)
preco_final  = max(preco_final, piso_projeto)
```

A **senioridade** entra via `valor_hora` (nao como multiplicador) para evitar dupla
contagem. Custos recorrentes (hospedagem/dominio/manutencao) ficam a parte.

## Regras

- Toda alteracao de preco vai em `precos.yaml`, nao no codigo.
- Todo input do usuario e validado (pydantic). Rejeitar negativos/zero.
- Preco final nunca abaixo do piso definido em `precos.yaml`.
- `core/pricing.py` permanece PURO e deterministico — sem I/O, sem print.
- Revisar `precos.yaml` a cada 6-12 meses; atualizar `meta.data_atualizacao`.

## Fora de escopo

Integracao com APIs externas, banco de dados, autenticacao, multi-usuario.

## Commit prefix

`projects/calculadora_site:` (convencao snake_case do monorepo).
