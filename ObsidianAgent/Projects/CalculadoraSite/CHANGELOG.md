# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [0.2.0] - 2026-06-27

### Adicionado (competitividade / atratividade ao cliente)

- **Desconto comercial** (`desconto_pct`): gera ancora "de/por" — `preco_cheio`
  (cheio) vs `preco_final` (com desconto) + `economia` do cliente. Nunca rebaixa o piso.
- **Arredondamento atrativo** (`arredondar`): arredonda o preco final "para baixo"
  a um numero comercial limpo (ex.: R$ 23.400) — nunca aumenta o preco nem fura o piso.
- **Classificacao de competitividade** (`competitividade`): posiciona o preco final
  ante a faixa de mercado (abaixo_mercado / competitivo / alinhado / premium / piso),
  exibida em PDF, TXT e na tabela do terminal.
- CLI: flags `--desconto` e `--arredondar/--sem-arredondar`. TUI: campo de desconto
  (%) e checkbox de arredondamento.

### Notas de auditoria

- Configuracoes-base (template, sem extras) ficam na metade inferior das faixas de
  mercado (competitivas). Multiplicadores opcionais (design/urgencia/capital) compoem
  e podem ultrapassar a faixa — o orcamento agora sinaliza isso como "premium" e
  oferece desconto/arredondamento para reposicionar de forma atrativa.

## [0.1.0] - 2026-06-27

### Adicionado

- Motor de cálculo puro e determinístico (`core/pricing.py`) com a fórmula
  consolidada horas × valor/hora × multiplicadores + add-ons fixos, sanity-check
  contra faixas de mercado e piso de projeto.
- Catálogo de preços externalizado (`config/precos.yaml`) com a tabela de mercado
  brasileira 2026 (13 tipos de site, 4 níveis de design, 4 senioridades,
  16 funcionalidades, hospedagem) e validação via pydantic v2.
- TUI interativa em Textual (`ui/tui_app.py`) com identidade visual ADVAN7Tech.
- Exportação em PDF com papel timbrado ADVAN7Tech (ReportLab), JSON e TXT.
- CLI Typer (`calcular`, `listar`) com modo interativo padrão (abre a TUI).
- Suíte de testes (48) cobrindo motor, catálogo, relatórios, render, CLI e TUI
  (cobertura ~97%); gates ruff + mypy --strict limpos.
