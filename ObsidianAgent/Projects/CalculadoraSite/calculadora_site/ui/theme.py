"""Tema e identidade visual ADVAN7Tech — fonte unica da verdade de estilo.

Cores e textos de marca usados tanto pela TUI (Textual) quanto pelo papel
timbrado do PDF (ReportLab). Tambem reune os formatadores pt-BR (moeda/percent)
para que numero apareca identico em todos os relatorios.
"""

from __future__ import annotations

from dataclasses import dataclass

# Re-exporta os formatadores pt-BR (modulo-folha) para uso como theme.formatar_*
from ..formatting import formatar_brl, formatar_horas, formatar_pct

__all__ = [
    "MARCA",
    "Marca",
    "build_textual_css",
    "formatar_brl",
    "formatar_horas",
    "formatar_pct",
]

# --------------------------------------------------------------------------- #
# Paleta (hex) — referenciada por Textual CSS e por reportlab.lib.colors
# --------------------------------------------------------------------------- #
AZUL_PROFUNDO = "#0B1F3A"  # navy — fundo do papel timbrado / barra de titulo
AZUL_MEDIO = "#13315C"
ACENTO = "#0FB9B1"  # teal — destaque da marca "7"
ACENTO_CLARO = "#16C79A"
TEXTO = "#1B2733"
TEXTO_SUAVE = "#5B6B7B"
CINZA_CLARO = "#E5E9EF"
CINZA_LINHA = "#C9D2DD"
BRANCO = "#FFFFFF"

VERDE_OK = "#2E9E5B"
AMBAR_ALERTA = "#C9852A"
VERMELHO = "#C0392B"

# status do sanity-check -> cor
COR_STATUS = {
    "ok": VERDE_OK,
    "acima_faixa": ACENTO,
    "abaixo_faixa": AMBAR_ALERTA,
    "abaixo_piso": VERMELHO,
}


@dataclass(frozen=True)
class Marca:
    """Textos da identidade ADVAN7Tech (papel timbrado)."""

    nome: str = "ADVAN7Tech"
    tagline: str = "Solucoes Web & Seguranca"
    site: str = "advan7.tech"
    contato: str = "contato@advan7.tech"
    documento: str = "Orcamento de Desenvolvimento Web"


MARCA = Marca()


# --------------------------------------------------------------------------- #
# CSS da TUI (Textual) - construido a partir da paleta acima
# --------------------------------------------------------------------------- #
def build_textual_css() -> str:
    """CSS do app Textual, gerado da paleta para manter uma so fonte de estilo."""
    return f"""
    Screen {{
        background: {AZUL_PROFUNDO};
        color: {BRANCO};
    }}
    #cabecalho {{
        height: 3;
        background: {ACENTO};
        color: {AZUL_PROFUNDO};
        content-align: center middle;
        text-style: bold;
    }}
    #corpo {{
        padding: 1 2;
    }}
    .secao {{
        border: round {ACENTO};
        padding: 0 1;
        margin: 1 0;
    }}
    .rotulo {{
        color: {ACENTO_CLARO};
        text-style: bold;
    }}
    #painel_resultado {{
        border: round {ACENTO_CLARO};
        padding: 1 1;
        margin: 1 0;
        height: auto;
    }}
    #barra_acoes {{
        height: auto;
        padding: 1 0;
    }}
    Button {{
        margin: 0 1;
    }}
    Button.acao {{
        background: {ACENTO};
        color: {AZUL_PROFUNDO};
        text-style: bold;
    }}
    Input, Select {{
        margin: 0 0 1 0;
    }}
    SelectionList {{
        height: 12;
        border: round {ACENTO};
        margin: 0 0 1 0;
    }}
    Checkbox {{
        margin: 0 0 1 0;
    }}
    """
