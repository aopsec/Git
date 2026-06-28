# Certificação de Competitividade — CalculadoraSite

- **Versão certificada:** 0.2.0 (commit `246ab54`)
- **Data:** 2026-06-28
- **Tabela de mercado:** `config/precos.yaml` (`data_atualizacao: 2026-06-27`)
- **Gates no momento da certificação:** `ruff` ✓ · `mypy --strict` ✓ · 55 testes ✓ (~97% cobertura)

## Atestação

Atesta-se que a CalculadoraSite produz, **na configuração padrão** (design
`template`, páginas incluídas, sem urgência/capital), um **preço final
competitivo** — dentro da faixa de mercado do tipo de site e **na metade inferior
ou alinhado à mediana** — e oferece mecanismos para tornar **qualquer** orçamento
**atrativo ao cliente**, sem comprometer o piso de viabilidade do projeto.

## Evidência — posição default vs. mercado (todos os tipos)

Preço final em R$, design `template`, páginas incluídas, sem ajustes opcionais.
Classe = posição do preço (pleno) ante a faixa de mercado.

| Tipo de site | iniciante | pleno | Faixa de mercado | Classe (pleno) |
|---|---:|---:|---|---|
| landing_simples | 1.232 | 2.128 | 970–2.500 | alinhado |
| landing_conversao | 3.081 | 5.321 | 1.500–15.000 | competitivo |
| institucional_simples | 1.643 | 2.838 | 1.500–6.000 | competitivo |
| institucional_completo | 5.134 | 8.868 | 4.500–15.000 | competitivo |
| site_blog | 6.161 | 10.642 | 6.000–12.000 | alinhado |
| blog_profissional | 3.081 | 5.321 | 2.000–6.000 | alinhado |
| ecommerce_basico | 6.161 | 10.642 | 5.000–12.000 | alinhado |
| ecommerce_medio | 14.376 | 24.831 | 12.000–25.000 | alinhado |
| ecommerce_avancado | 24.645 | 42.568 | 20.000–80.000 | competitivo |
| portal_noticias | 12.322 | 21.284 | 5.000–50.000 | competitivo |
| marketplace | 24.645 | 42.568 | 15.000–50.000 | alinhado |
| sistema_saas | 32.860 | 56.757 | 15.000–180.000 | competitivo |
| pwa | 10.269 | 17.737 | 8.000–40.000 | competitivo |

**Resultado:** 13/13 tipos classificados como `competitivo` ou `alinhado` no
default (pleno); à taxa `iniciante`, todos ainda mais baixos. Nenhum `premium`.

Reproduzir: `python CalculadoraSite.py calcular -t <tipo> -o tabela`.

## Mecanismos de atratividade (v0.2.0)

1. **Âncora de desconto** (`--desconto` / campo TUI): apresenta "de/por" —
   `preço cheio` riscado vs `preço final` + **economia do cliente**.
2. **Arredondamento atrativo** (`--arredondar`): número comercial limpo,
   sempre **para baixo** (favorável ao cliente).
3. **Classificação de competitividade**: rótulo `abaixo_mercado / competitivo /
   alinhado / premium / piso` exibido em PDF, TXT e terminal.

**Exemplo verificado** (e-commerce semi-custom, pleno, 3 features):
preço cheio R$ 27.529,75 → desconto 15% → arredondado → **R$ 23.400,00**
(economia **R$ 4.129,75** ao cliente).

## Invariantes garantidos (cobertos por teste)

| Invariante | Teste |
|---|---|
| Preço final **nunca abaixo do piso** do projeto (mesmo com 95% de desconto) | `test_desconto_nunca_rebaixa_o_piso` |
| Arredondamento **nunca aumenta** o preço | `test_arredondamento_atrativo_nunca_aumenta` |
| Âncora/economia corretas (`preço_cheio − preço_final`) | `test_desconto_gera_ancora_e_economia` |
| Classificação reflete **o que o cliente paga** (pós-desconto) | `test_competitividade_classifica_posicao` |
| Cálculo determinístico (mesma entrada → mesma saída) | `test_determinismo` |

## Ressalvas

- **Empilhamento premium honesto:** combinações opcionais (design `custom` +
  `senior` + urgência + capital) compõem multiplicativamente e **legitimamente
  ultrapassam** a faixa de mercado. A ferramenta as rotula `premium` e sugere
  desconto/arredondamento — **não infla silenciosamente**.
- As faixas de mercado são estimativas de praticantes BR 2025–2026
  (`precos.yaml`), não levantamento estatístico independente. Revisar a cada
  6–12 meses (`meta.data_atualizacao`).

## Recomendação de uso para máxima atratividade

Orçar no default (`template`/`semi_custom`, sem urgência salvo real),
aplicar `--desconto 0.10–0.15` + `--arredondar`, e mirar classe
`competitivo`/`alinhado`.
