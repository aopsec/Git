"""Geracao do PDF de orcamento com papel timbrado ADVAN7Tech (ReportLab).

A marca (barra superior navy com o wordmark ADVAN7Tech + tagline e a faixa de
rodape com contato/data) e desenhada em TODAS as paginas por um callback de
canvas. O corpo usa Platypus (tabelas) para o detalhamento do orcamento.

Todas as cores e textos de marca vem de :mod:`calculadora_site.ui.theme` -
fonte unica de estilo, compartilhada com a TUI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..core.models import Orcamento
from ..ui import theme

# cores reportlab derivadas da paleta do tema
_NAVY = colors.HexColor(theme.AZUL_PROFUNDO)
_ACENTO = colors.HexColor(theme.ACENTO)
_ACENTO_CLARO = colors.HexColor(theme.ACENTO_CLARO)
_TEXTO = colors.HexColor(theme.TEXTO)
_TEXTO_SUAVE = colors.HexColor(theme.TEXTO_SUAVE)
_CINZA_CLARO = colors.HexColor(theme.CINZA_CLARO)
_CINZA_LINHA = colors.HexColor(theme.CINZA_LINHA)

_MARGEM = 1.6 * cm
_BANDA_TOPO = 2.4 * cm
_LARGURA_UTIL = A4[0] - 2 * _MARGEM


def _cor_status(status: str) -> colors.Color:
    return colors.HexColor(theme.COR_STATUS.get(status, theme.ACENTO))


# --------------------------------------------------------------------------- #
# Papel timbrado (desenhado em cada pagina)
# --------------------------------------------------------------------------- #
def _desenhar_timbrado(canvas: Any, doc: Any, orcamento: Orcamento) -> None:
    largura, altura = A4
    canvas.saveState()

    # barra superior
    canvas.setFillColor(_NAVY)
    canvas.rect(0, altura - _BANDA_TOPO, largura, _BANDA_TOPO, fill=1, stroke=0)
    canvas.setFillColor(_ACENTO)
    canvas.rect(0, altura - _BANDA_TOPO - 0.10 * cm, largura, 0.10 * cm, fill=1, stroke=0)

    # wordmark "ADVAN7Tech" (7 em destaque)
    base_y = altura - 1.45 * cm
    x = _MARGEM
    canvas.setFont("Helvetica-Bold", 22)
    canvas.setFillColor(colors.white)
    canvas.drawString(x, base_y, "ADVAN")
    x += canvas.stringWidth("ADVAN", "Helvetica-Bold", 22)
    canvas.setFillColor(_ACENTO)
    canvas.drawString(x, base_y, "7")
    x += canvas.stringWidth("7", "Helvetica-Bold", 22)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 22)
    canvas.drawString(x, base_y, "Tech")

    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(_CINZA_CLARO)
    canvas.drawString(_MARGEM, base_y - 0.55 * cm, theme.MARCA.tagline)

    # titulo do documento (direita)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.setFillColor(_ACENTO_CLARO)
    canvas.drawRightString(largura - _MARGEM, base_y, "ORCAMENTO")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.white)
    canvas.drawRightString(largura - _MARGEM, base_y - 0.5 * cm, f"Emissao: {orcamento.data}")

    # rodape
    canvas.setFillColor(_ACENTO)
    canvas.rect(0, 1.0 * cm, largura, 0.05 * cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(_TEXTO_SUAVE)
    rodape = (
        f"{theme.MARCA.site}   |   {theme.MARCA.contato}   |   "
        f"Tabela de referencia: {orcamento.data_tabela}"
    )
    canvas.drawString(_MARGEM, 0.58 * cm, rodape)
    canvas.drawRightString(largura - _MARGEM, 0.58 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


# --------------------------------------------------------------------------- #
# Estilos e tabelas do corpo
# --------------------------------------------------------------------------- #
def _estilos() -> dict[str, ParagraphStyle]:
    return {
        "secao": ParagraphStyle(
            "secao",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=_NAVY,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "normal": ParagraphStyle(
            "normal", fontName="Helvetica", fontSize=9.5, textColor=_TEXTO, leading=13
        ),
        "aviso": ParagraphStyle(
            "aviso",
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=_TEXTO_SUAVE,
            leading=11,
            alignment=TA_LEFT,
            spaceBefore=8,
        ),
    }


def _tabela_kv(linhas: list[tuple[str, str]], total_idx: int | None = None) -> Table:
    """Tabela descricao | valor (valor alinhado a direita). ``total_idx`` recebe
    realce (linha de subtotal/total)."""
    tabela = Table(linhas, colWidths=[_LARGURA_UTIL * 0.68, _LARGURA_UTIL * 0.32])
    estilo = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), _TEXTO),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, _CINZA_LINHA),
    ]
    if total_idx is not None:
        estilo += [
            ("FONT", (0, total_idx), (-1, total_idx), "Helvetica-Bold", 10),
            ("LINEABOVE", (0, total_idx), (-1, total_idx), 0.8, _NAVY),
        ]
    tabela.setStyle(TableStyle(estilo))
    return tabela


def _caixa_preco_final(orcamento: Orcamento) -> Table:
    """Faixa de destaque com o PRECO FINAL."""
    rotulo = "PRECO FINAL" + (" (piso do projeto)" if orcamento.piso_acionado else "")
    tabela = Table(
        [[rotulo, theme.formatar_brl(orcamento.preco_final)]],
        colWidths=[_LARGURA_UTIL * 0.58, _LARGURA_UTIL * 0.42],
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _NAVY),
                ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
                ("TEXTCOLOR", (1, 0), (1, 0), _ACENTO),
                ("FONT", (0, 0), (0, 0), "Helvetica-Bold", 13),
                ("FONT", (1, 0), (1, 0), "Helvetica-Bold", 16),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return tabela


def _nota_sanity(orcamento: Orcamento, estilos: dict[str, ParagraphStyle]) -> Table:
    """Faixa colorida com a mensagem do sanity-check."""
    cor = _cor_status(orcamento.sanity.status)
    estilo_txt = ParagraphStyle(
        "sanity", parent=estilos["normal"], fontSize=8.5, textColor=colors.white, leading=11
    )
    par = Paragraph(orcamento.sanity.mensagem, estilo_txt)
    tabela = Table([[par]], colWidths=[_LARGURA_UTIL])
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), cor),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return tabela


def _bloco_fechamento(orcamento: Orcamento, est: dict[str, ParagraphStyle]) -> list[Flowable]:
    """Ajustes + ancora de desconto + caixa de preco + competitividade + sanity."""
    brl = theme.formatar_brl
    ajustes = []
    if orcamento.urgencia_pct:
        ajustes.append(("Urgencia", f"+{theme.formatar_pct(orcamento.urgencia_pct)}"))
    if orcamento.localizacao_pct:
        ajustes.append(("Localizacao capital", f"+{theme.formatar_pct(orcamento.localizacao_pct)}"))
    ajustes.append(("Margem de lucro", f"+{theme.formatar_pct(orcamento.margem_lucro_pct)}"))
    ajustes.append(("Carga tributaria (gross-up)", theme.formatar_pct(orcamento.carga_tributaria_pct)))

    flow: list[Flowable] = [
        Paragraph("Ajustes aplicados", est["secao"]),
        _tabela_kv(ajustes),
        Spacer(1, 6),
    ]
    if orcamento.economia > 0:
        anc = f"De <strike>{brl(orcamento.preco_cheio)}</strike>"
        if orcamento.desconto_pct:
            anc += f" com desconto de {theme.formatar_pct(orcamento.desconto_pct)}"
        anc += f" - economia de {brl(orcamento.economia)} para o cliente"
        flow.append(Paragraph(anc, est["aviso"]))
    flow.append(_caixa_preco_final(orcamento))
    flow.append(Spacer(1, 4))
    flow.append(Paragraph(f"Posicao de mercado: {orcamento.competitividade_label}.", est["normal"]))
    flow.append(Spacer(1, 6))
    flow.append(_nota_sanity(orcamento, est))
    return flow


def _construir_corpo(orcamento: Orcamento) -> list[Flowable]:
    est = _estilos()
    brl = theme.formatar_brl
    flow: list[Flowable] = []

    # metadados
    meta_linhas = []
    if orcamento.cliente:
        meta_linhas.append(("Cliente", orcamento.cliente))
    if orcamento.projeto:
        meta_linhas.append(("Projeto", orcamento.projeto))
    meta_linhas.append(("Tipo de site", orcamento.tipo_nome))
    meta_linhas.append(("Validade da proposta", f"{orcamento.validade_dias} dias"))
    meta = Table(
        [[f"{k}:", v] for k, v in meta_linhas], colWidths=[_LARGURA_UTIL * 0.28, _LARGURA_UTIL * 0.72]
    )
    meta.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9.5),
                ("FONT", (1, 0), (1, -1), "Helvetica", 9.5),
                ("TEXTCOLOR", (0, 0), (-1, -1), _TEXTO),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ]
        )
    )
    flow.append(meta)

    # escopo (horas)
    flow.append(Paragraph("Escopo (horas estimadas)", est["secao"]))
    escopo = [(i.descricao, theme.formatar_horas(i.horas)) for i in orcamento.itens_escopo]
    escopo.append((f"Overhead ({theme.formatar_pct(orcamento.overhead_pct)})",
                   theme.formatar_horas(orcamento.horas_overhead)))
    escopo.append(("Horas totais", theme.formatar_horas(orcamento.horas_total)))
    flow.append(_tabela_kv(escopo, total_idx=len(escopo) - 1))

    # composicao
    flow.append(Paragraph("Composicao financeira", est["secao"]))
    comp = [
        ("Valor/hora", brl(orcamento.valor_hora)),
        (f"Multiplicador de design (x{orcamento.mult_design:g})",
         brl(orcamento.subtotal_dev) + "  (subtotal dev.)"),
    ]
    for addon in orcamento.addons:
        comp.append((f"Add-on: {addon.descricao}", brl(addon.valor)))
    comp.append(("Subtotal", brl(orcamento.subtotal)))
    flow.append(_tabela_kv(comp, total_idx=len(comp) - 1))

    # ajustes + fechamento (preco/competitividade/sanity)
    flow.extend(_bloco_fechamento(orcamento, est))

    # recorrentes
    if orcamento.recorrentes:
        flow.append(Paragraph("Custos recorrentes (a parte do preco do projeto)", est["secao"]))
        rec_linhas = []
        for rec in orcamento.recorrentes:
            mensal = f"{brl(rec.valor_mensal)}/mes" if rec.valor_mensal else "-"
            anual = f"{brl(rec.valor_anual)}/ano" if rec.valor_anual else "-"
            rec_linhas.append((rec.descricao, f"{mensal}   {anual}"))
        flow.append(_tabela_kv(rec_linhas))

    flow.append(Paragraph(f"Aviso: {orcamento.aviso}", est["aviso"]))
    return flow


def gerar_pdf(orcamento: Orcamento, caminho: Path | str) -> Path:
    """Gera o PDF do orcamento com papel timbrado ADVAN7Tech em ``caminho``."""
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        leftMargin=_MARGEM,
        rightMargin=_MARGEM,
        topMargin=_BANDA_TOPO + 0.8 * cm,
        bottomMargin=1.6 * cm,
        title=f"Orcamento {theme.MARCA.nome} - {orcamento.cliente or orcamento.tipo_nome}",
        author=theme.MARCA.nome,
    )

    def _on_page(canvas: Any, doc_ref: Any) -> None:
        _desenhar_timbrado(canvas, doc_ref, orcamento)

    doc.build(_construir_corpo(orcamento), onFirstPage=_on_page, onLaterPages=_on_page)
    return destino
