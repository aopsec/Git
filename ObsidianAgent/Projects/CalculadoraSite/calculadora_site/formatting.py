"""Formatadores pt-BR puros (moeda/percent/horas), sem dependencias.

Modulo-folha: pode ser importado por qualquer camada (core, ui, reports) sem
criar dependencia circular. Nao usa locale do SO -> saida deterministica.
"""

from __future__ import annotations


def formatar_brl(valor: float, *, centavos: bool = True) -> str:
    """123456.7 -> 'R$ 123.456,70'. Com ``centavos=False`` -> 'R$ 123.457'."""
    casas = 2 if centavos else 0
    base = f"{valor:,.{casas}f}"  # en-US: '123,456.70'
    trocado = base.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"R$ {trocado}"


def formatar_pct(fracao: float) -> str:
    """0.35 -> '35%'; 0.205 -> '20,5%'."""
    pct = f"{fracao * 100:.1f}".rstrip("0").rstrip(".")
    return f"{pct.replace('.', ',')}%"


def formatar_horas(horas: float) -> str:
    """21.6 -> '21,6h'; 15.0 -> '15h'."""
    txt = f"{horas:.1f}".rstrip("0").rstrip(".")
    return f"{txt.replace('.', ',')}h"
