# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

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
