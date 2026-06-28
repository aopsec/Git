# CalculadoraSite

Calculadora de **precificação de sites** para o mercado brasileiro (2026), em
terminal. Coleta o escopo de um projeto via wizard interativo (TUI) ou por flags
(CLI) e gera um orçamento profissional em **PDF com papel timbrado ADVAN7Tech**,
além de **JSON** (auditável) e **TXT**.

> ⚠️ Orçamento **estimativo**: os valores são referências de mercado para
> ancoragem, não uma cotação fechada. Revise o `precos.yaml` a cada 6–12 meses.

## Recursos

- Motor de cálculo **puro e determinístico** (mesma entrada → mesma saída).
- Modelo **aditivo e transparente** (estilo Dekassegui) + **bandas de mercado BR**:
  horas × valor/hora × multiplicadores + add-ons fixos.
- **Sanity-check**: compara o preço final com a faixa de mercado do tipo de site
  e alerta sobre subprecificação ou escopo premium.
- Preços, horas e multiplicadores **100% externalizados** em `precos.yaml`.
- Exportação em **PDF (timbrado), JSON e TXT**.

## Instalação

Requer Python 3.11+.

```bash
cd ObsidianAgent/Projects/CalculadoraSite
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# ou, como pacote instalável (expõe o comando `calculadora-site`):
pip install -e .
```

## Uso

### Modo interativo (TUI)

```bash
python CalculadoraSite.py
```

Preencha as seções (cliente, tipo de site, páginas, design, senioridade,
funcionalidades, urgência, hospedagem…), clique **Calcular** (ou `F2`) e
exporte em PDF/JSON/TXT. Os arquivos vão para `./orcamentos/`.

### Modo não interativo (CLI)

```bash
# listar os slugs disponíveis no catálogo
python CalculadoraSite.py listar

# orçar e imprimir a tabela no terminal
python CalculadoraSite.py calcular -t institucional_simples -p 5 -s iniciante

# orçar um e-commerce e exportar PDF + JSON
python CalculadoraSite.py calcular \
  -t ecommerce_basico -p 12 -d semi_custom -s pleno \
  -f gateway_pagamento -f controle_estoque -f seo_avancado \
  --urgencia --hospedagem vps --dominio --manutencao 300 \
  --cliente "Loja Exemplo" -o pdf -o json --out-file ./orcamentos/loja
```

Principais flags do `calcular`:

| Flag | Descrição |
|---|---|
| `-t, --tipo` | Slug do tipo de site (obrigatório). |
| `-p, --paginas` | Número de páginas. |
| `-d, --design` | `template` / `semi_custom` / `custom` / `premium`. |
| `-s, --senioridade` | `iniciante` / `pleno` / `senior` / `agencia` (define o valor/hora). |
| `--valor-hora` / `--meta-mensal` | Sobrescreve o valor/hora (ou deriva de meta líquida). |
| `-f, --funcionalidade` | Add-on (repetível). |
| `--urgencia`, `--capital` | Ajustes de urgência (+20%) e localização capital (+30%). |
| `--margem`, `--tributo` | Frações, ex.: `0.3` e `0.06`. |
| `--hospedagem`, `--dominio`, `--manutencao` | Custos recorrentes (listados à parte). |
| `-o, --output` | `tabela` / `pdf` / `json` / `txt` (repetível). |
| `--precos` | Caminho de um `precos.yaml` alternativo. |

## Como o preço é calculado

```
horas_total  = (horas_base + paginas_extra*h/pág + Σ horas_features) * (1 + overhead%)
subtotal     = horas_total * valor_hora * mult_design + Σ add_ons_fixos
preço_final  = subtotal * (1+urgência%) * (1+localização%) * (1+margem%) / (1 - tributo%)
preço_final  = max(preço_final, piso_projeto)
```

A **senioridade entra via valor/hora** (não como multiplicador separado), evitando
dupla contagem. Custos recorrentes (hospedagem, domínio `.com.br` R$ 40/ano,
manutenção) ficam **fora** do preço do projeto, listados à parte.

Detalhe completo no docstring de [`core/pricing.py`](calculadora_site/core/pricing.py).

### Competitividade e atratividade

O preço default fica competitivo/alinhado ao mercado; para deixar a oferta
atrativa há `--desconto` (âncora "de/por" + economia), `--arredondar`
(número limpo, nunca aumenta) e a classificação de competitividade exibida no
orçamento. Atestação e evidência completas em [CERTIFICACAO.md](CERTIFICACAO.md).

## Editar preços

Toda tabela (tipos de site, horas-base, valores/hora, add-ons, multiplicadores,
parâmetros) vive em [`calculadora_site/config/precos.yaml`](calculadora_site/config/precos.yaml).
**Nunca** edite preços no código. Após alterar, rode os testes (a suíte valida que
configurações representativas continuam dentro das faixas de mercado).

## Desenvolvimento

```bash
pip install -e '.[dev]'
ruff check .            # lint
mypy calculadora_site   # type-check (--strict)
pytest                  # 48 testes
pytest --cov=calculadora_site --cov-report=term-missing   # cobertura (~97%)
```

Arquitetura e convenções: ver [CLAUDE.md](CLAUDE.md).

## Fora de escopo

Integração com APIs externas, banco de dados, autenticação e multiusuário.
