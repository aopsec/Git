"""Renderizacao Rich do orcamento - compartilhada entre a TUI e a CLI.

Produz um renderable Rich (tabelas + paineis) consumido tanto pelo painel de
resultado do app Textual quanto pela saida ``--output tabela`` da CLI.
"""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..core.models import Orcamento
from . import theme

_BORDA = theme.ACENTO


def _tabela(titulo: str) -> Table:
    t = Table(title=titulo, title_justify="left", expand=True, border_style=theme.TEXTO_SUAVE)
    t.add_column("Item")
    t.add_column("Valor", justify="right")
    return t


def painel_orcamento(orc: Orcamento) -> RenderableType:
    brl = theme.formatar_brl
    blocos: list[RenderableType] = []

    # --- cabecalho ---
    cab = Text()
    cab.append(f"{theme.MARCA.nome} ", style=f"bold {theme.ACENTO}")
    cab.append("- Orcamento de Desenvolvimento Web\n", style="bold")
    if orc.cliente:
        cab.append(f"Cliente: {orc.cliente}\n")
    if orc.projeto:
        cab.append(f"Projeto: {orc.projeto}\n")
    cab.append(f"Tipo: {orc.tipo_nome}   |   Emissao: {orc.data}   |   Validade: {orc.validade_dias} dias")
    blocos.append(Panel(cab, border_style=_BORDA))

    # --- horas ---
    th = _tabela("Escopo (horas)")
    for item in orc.itens_escopo:
        th.add_row(item.descricao, theme.formatar_horas(item.horas))
    th.add_row(
        f"Overhead ({theme.formatar_pct(orc.overhead_pct)})",
        theme.formatar_horas(orc.horas_overhead),
    )
    th.add_row(Text("Horas totais", style="bold"), Text(theme.formatar_horas(orc.horas_total), style="bold"))
    blocos.append(th)

    # --- composicao ---
    tc = _tabela("Composicao financeira")
    tc.add_row("Valor/hora", brl(orc.valor_hora))
    tc.add_row(f"Multiplicador de design (x{orc.mult_design:g})", "")
    tc.add_row("Subtotal desenvolvimento", brl(orc.subtotal_dev))
    for addon in orc.addons:
        tc.add_row(f"Add-on: {addon.descricao}", brl(addon.valor))
    tc.add_row(Text("Subtotal", style="bold"), Text(brl(orc.subtotal), style="bold"))
    if orc.urgencia_pct:
        tc.add_row("Urgencia", f"+{theme.formatar_pct(orc.urgencia_pct)}")
    if orc.localizacao_pct:
        tc.add_row("Localizacao capital", f"+{theme.formatar_pct(orc.localizacao_pct)}")
    tc.add_row("Margem de lucro", f"+{theme.formatar_pct(orc.margem_lucro_pct)}")
    tc.add_row("Carga tributaria", theme.formatar_pct(orc.carga_tributaria_pct))
    blocos.append(tc)

    # --- preco final ---
    rotulo = "PRECO FINAL" + (" (piso do projeto)" if orc.piso_acionado else "")
    preco = Text(f"{rotulo}: {brl(orc.preco_final)}", style=f"bold {theme.ACENTO}")
    blocos.append(Panel(preco, border_style=theme.ACENTO_CLARO))

    # --- sanity ---
    cor = theme.COR_STATUS.get(orc.sanity.status, theme.ACENTO)
    blocos.append(Panel(Text(orc.sanity.mensagem, style=cor), title="Faixa de mercado", border_style=cor))

    # --- recorrentes ---
    if orc.recorrentes:
        tr = _tabela("Custos recorrentes (a parte)")
        for rec in orc.recorrentes:
            mensal = f"{brl(rec.valor_mensal)}/mes" if rec.valor_mensal else "-"
            anual = f"{brl(rec.valor_anual)}/ano" if rec.valor_anual else "-"
            tr.add_row(rec.descricao, f"{mensal}   {anual}")
        blocos.append(tr)

    return Group(*blocos)
