"""Exportacao do orcamento para texto puro (TXT) com cabecalho ADVAN7Tech.

Saida deterministica e legivel em qualquer terminal. Os mesmos numeros do PDF,
sem dependencia grafica.
"""

from __future__ import annotations

from pathlib import Path

from ..core.models import Orcamento
from ..ui import theme

LARGURA = 64


def _regua(caractere: str = "=") -> str:
    return caractere * LARGURA


def _linha_valor(rotulo: str, valor: str, recuo: int = 2) -> str:
    """Rotulo a esquerda, valor alinhado a direita dentro de LARGURA."""
    esq = " " * recuo + rotulo
    espaco = max(LARGURA - len(esq) - len(valor), 1)
    return esq + " " * espaco + valor


def _bloco_preco_final(orcamento: Orcamento) -> list[str]:
    """Bloco de fechamento: ancora de desconto, preco final, economia, competitividade."""
    brl = theme.formatar_brl
    linhas = ["  " + "-" * (LARGURA - 2)]
    if orcamento.economia > 0:
        linhas.append(_linha_valor("Preco cheio (de)", brl(orcamento.preco_cheio)))
        if orcamento.desconto_pct:
            linhas.append(
                _linha_valor("Desconto comercial", f"-{theme.formatar_pct(orcamento.desconto_pct)}")
            )
    rotulo = "PRECO FINAL (por)" if orcamento.economia > 0 else "PRECO FINAL"
    linhas.append(_linha_valor(rotulo, brl(orcamento.preco_final)))
    if orcamento.economia > 0:
        linhas.append(_linha_valor("Economia do cliente", brl(orcamento.economia)))
    if orcamento.piso_acionado:
        linhas.append(_linha_valor("(piso do projeto aplicado)", brl(orcamento.piso_aplicado)))
    linhas.append(_linha_valor("Competitividade", orcamento.competitividade_label))
    linhas.append("")
    return linhas


def _bloco_recorrentes(orcamento: Orcamento) -> list[str]:
    """Secao de custos recorrentes (vazia se nao houver)."""
    if not orcamento.recorrentes:
        return []
    brl = theme.formatar_brl
    linhas = ["CUSTOS RECORRENTES (a parte do preco do projeto)"]
    for rec in orcamento.recorrentes:
        mensal = f"{brl(rec.valor_mensal)}/mes" if rec.valor_mensal else "-"
        anual = f"{brl(rec.valor_anual)}/ano" if rec.valor_anual else "-"
        linhas.append(_linha_valor(rec.descricao, f"{mensal}   {anual}"))
    if orcamento.total_recorrente_mensal:
        linhas.append(
            _linha_valor(
                "Total recorrente mensal", f"{brl(orcamento.total_recorrente_mensal)}/mes"
            )
        )
    linhas.append("")
    return linhas


def orcamento_para_txt(orcamento: Orcamento) -> str:
    m = theme.MARCA
    brl = theme.formatar_brl
    linhas: list[str] = []

    # --- cabecalho / papel timbrado ---
    linhas.append(_regua("="))
    linhas.append(f"  {m.nome} - {m.tagline}")
    linhas.append(f"  {m.documento}")
    linhas.append(_regua("="))
    if orcamento.cliente:
        linhas.append(f"Cliente : {orcamento.cliente}")
    if orcamento.projeto:
        linhas.append(f"Projeto : {orcamento.projeto}")
    linhas.append(f"Data    : {orcamento.data}    Validade: {orcamento.validade_dias} dias")
    linhas.append(f"Tipo    : {orcamento.tipo_nome}")
    linhas.append("")

    # --- escopo (horas) ---
    linhas.append("ESCOPO (horas)")
    for item in orcamento.itens_escopo:
        linhas.append(_linha_valor(item.descricao, theme.formatar_horas(item.horas)))
    linhas.append("  " + "-" * (LARGURA - 2))
    linhas.append(_linha_valor("Horas de desenvolvimento", theme.formatar_horas(orcamento.horas_dev)))
    linhas.append(
        _linha_valor(
            f"Overhead ({theme.formatar_pct(orcamento.overhead_pct)})",
            theme.formatar_horas(orcamento.horas_overhead),
        )
    )
    linhas.append(_linha_valor("Horas totais", theme.formatar_horas(orcamento.horas_total)))
    linhas.append("")

    # --- composicao financeira ---
    linhas.append("COMPOSICAO")
    linhas.append(_linha_valor("Valor/hora", brl(orcamento.valor_hora)))
    linhas.append(_linha_valor("Multiplicador de design", f"x{orcamento.mult_design:g}"))
    linhas.append(_linha_valor("Subtotal desenvolvimento", brl(orcamento.subtotal_dev)))
    if orcamento.addons:
        linhas.append("  Add-ons (preco fixo):")
        for addon in orcamento.addons:
            linhas.append(_linha_valor(addon.descricao, brl(addon.valor), recuo=4))
        linhas.append(_linha_valor("Subtotal add-ons", brl(orcamento.subtotal_addons)))
    linhas.append(_linha_valor("Subtotal", brl(orcamento.subtotal)))
    linhas.append("")

    # --- ajustes finais ---
    linhas.append("AJUSTES")
    if orcamento.urgencia_pct:
        linhas.append(_linha_valor("Urgencia", f"+{theme.formatar_pct(orcamento.urgencia_pct)}"))
    if orcamento.localizacao_pct:
        linhas.append(
            _linha_valor("Localizacao capital", f"+{theme.formatar_pct(orcamento.localizacao_pct)}")
        )
    linhas.append(_linha_valor("Margem de lucro", f"+{theme.formatar_pct(orcamento.margem_lucro_pct)}"))
    linhas.append(
        _linha_valor("Carga tributaria", theme.formatar_pct(orcamento.carga_tributaria_pct))
    )
    linhas.extend(_bloco_preco_final(orcamento))

    # --- sanity-check ---
    marcador = {"ok": "[OK]", "acima_faixa": "[i]", "abaixo_faixa": "[!]", "abaixo_piso": "[!!]"}
    linhas.append(f"{marcador.get(orcamento.sanity.status, '[i]')} {orcamento.sanity.mensagem}")
    linhas.append("")

    # --- recorrentes ---
    linhas.extend(_bloco_recorrentes(orcamento))

    # --- rodape ---
    linhas.append(_regua("-"))
    linhas.append(f"Aviso: {orcamento.aviso}")
    linhas.append(f"Tabela de referencia: {orcamento.data_tabela}  |  {m.site}  |  {m.contato}")
    return "\n".join(linhas)


def exportar_txt(orcamento: Orcamento, caminho: Path | str) -> Path:
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(orcamento_para_txt(orcamento) + "\n", encoding="utf-8")
    return destino
