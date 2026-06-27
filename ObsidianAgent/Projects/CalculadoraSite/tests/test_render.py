"""Teste do renderer Rich compartilhado (TUI/CLI)."""

from __future__ import annotations

from rich.console import Console

from calculadora_site.core.models import Catalogo, ProjetoInput
from calculadora_site.core.pricing import calcular
from calculadora_site.ui.render import painel_orcamento


def test_painel_renderiza_orcamento_completo(catalogo_real: Catalogo) -> None:
    entrada = ProjetoInput(
        tipo="institucional_completo",
        paginas=12,
        nivel_design="custom",
        senioridade="senior",
        funcionalidades=["blog_cms", "chat_whatsapp", "seo_avancado"],
        urgencia=True,
        localizacao_capital=True,
        hospedagem="vps",
        incluir_dominio=True,
        manutencao_mensal=300,
        cliente="ACME Comunicacao",
        projeto="Portal institucional",
    )
    orc = calcular(entrada, catalogo_real)

    console = Console(width=90, record=True)
    console.print(painel_orcamento(orc))
    texto = console.export_text()

    assert "ACME Comunicacao" in texto
    assert "Portal institucional" in texto
    assert "PRECO FINAL" in texto
    assert "Hospedagem" in texto
    assert "Urgencia" in texto
