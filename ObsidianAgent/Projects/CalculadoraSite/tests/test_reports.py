"""Testes de exportacao (JSON / TXT / PDF) e formatadores pt-BR."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from calculadora_site.core.models import Catalogo, ProjetoInput
from calculadora_site.core.pricing import calcular
from calculadora_site.reports import json_export, pdf_report, txt_export
from calculadora_site.ui import theme


@pytest.fixture
def orcamento(catalogo_real: Catalogo):
    entrada = ProjetoInput(
        tipo="institucional_completo",
        paginas=10,
        nivel_design="semi_custom",
        senioridade="pleno",
        funcionalidades=["blog_cms", "seo_avancado", "chat_whatsapp"],
        urgencia=True,
        desconto_pct=0.12,
        arredondar=True,
        hospedagem="vps",
        incluir_dominio=True,
        manutencao_mensal=300,
        cliente="Cliente Exemplo Ltda",
        projeto="Site institucional",
    )
    return calcular(entrada, catalogo_real)


# --- formatadores -----------------------------------------------------------
def test_formatar_brl() -> None:
    assert theme.formatar_brl(1234.5) == "R$ 1.234,50"
    assert theme.formatar_brl(1234567.89) == "R$ 1.234.567,89"
    assert theme.formatar_brl(0) == "R$ 0,00"


def test_formatar_pct() -> None:
    assert theme.formatar_pct(0.35) == "35%"
    assert theme.formatar_pct(0.06) == "6%"
    assert theme.formatar_pct(0.205) == "20,5%"


def test_formatar_horas() -> None:
    assert theme.formatar_horas(21.6) == "21,6h"
    assert theme.formatar_horas(15.0) == "15h"


# --- JSON -------------------------------------------------------------------
def test_json_roundtrip(orcamento) -> None:
    texto = json_export.orcamento_para_json(orcamento)
    dados = json.loads(texto)
    assert dados["preco_final"] == orcamento.preco_final
    assert dados["tipo_slug"] == "institucional_completo"
    assert "sanity" in dados


def test_exportar_json_grava_arquivo(orcamento, tmp_path: Path) -> None:
    destino = json_export.exportar_json(orcamento, tmp_path / "orc.json")
    assert destino.exists()
    dados = json.loads(destino.read_text(encoding="utf-8"))
    assert dados["preco_final"] == orcamento.preco_final


# --- TXT --------------------------------------------------------------------
def test_txt_contem_marca_e_preco(orcamento) -> None:
    texto = txt_export.orcamento_para_txt(orcamento)
    assert "ADVAN7Tech" in texto
    assert "PRECO FINAL" in texto
    assert theme.formatar_brl(orcamento.preco_final) in texto
    # recorrentes presentes
    assert "Hospedagem" in texto
    assert "Manutencao" in texto


def test_exportar_txt_grava_arquivo(orcamento, tmp_path: Path) -> None:
    destino = txt_export.exportar_txt(orcamento, tmp_path / "orc.txt")
    assert destino.exists()
    assert "ADVAN7Tech" in destino.read_text(encoding="utf-8")


def test_txt_mostra_desconto_e_competitividade(catalogo_real: Catalogo) -> None:
    entrada = ProjetoInput(
        tipo="institucional_completo",
        paginas=10,
        nivel_design="semi_custom",
        senioridade="pleno",
        desconto_pct=0.15,
        arredondar=True,
        cliente="Cliente X",
    )
    orc = calcular(entrada, catalogo_real)
    texto = txt_export.orcamento_para_txt(orc)
    assert "Preco cheio (de)" in texto
    assert "Desconto comercial" in texto
    assert "Economia do cliente" in texto
    assert "Competitividade" in texto


# --- PDF --------------------------------------------------------------------
def test_pdf_gera_arquivo_valido(orcamento, tmp_path: Path) -> None:
    destino = pdf_report.gerar_pdf(orcamento, tmp_path / "orc.pdf")
    assert destino.exists()
    conteudo = destino.read_bytes()
    assert conteudo.startswith(b"%PDF")
    assert len(conteudo) > 1500  # nao e um stub vazio
