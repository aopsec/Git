"""Testes do motor de calculo puro.

Provam a formula consolidada com valores calculados a mao sobre o
`catalogo_fake` (numeros redondos), independente dos dados de mercado.
"""

from __future__ import annotations

import pytest

from calculadora_site.core.models import Catalogo, ProjetoInput
from calculadora_site.core.pricing import PrecificacaoError, calcular

CENT = 0.01  # tolerancia de centavos para ruido de ponto flutuante


def test_caso_canonico_simples(catalogo_fake: Catalogo) -> None:
    """basico, 2 pag (sem extra), flat, vh=100, sem extras.

    horas_total = 10 * (1+0.5) = 15
    subtotal_dev = 15 * 100 * 1.0 = 1500
    apos_margem = 1500 * 1.25 = 1875
    preco_final = 1875 / (1-0.2) = 2343.75
    """
    entrada = ProjetoInput(tipo="basico", paginas=2, nivel_design="flat", senioridade="cem")
    orc = calcular(entrada, catalogo_fake)

    assert orc.valor_hora == 100.0
    assert orc.horas_dev == 10.0
    assert orc.horas_overhead == 5.0
    assert orc.horas_total == 15.0
    assert orc.subtotal_dev == pytest.approx(1500.0, abs=CENT)
    assert orc.preco_apos_margem == pytest.approx(1875.0, abs=CENT)
    assert orc.preco_final == pytest.approx(2343.75, abs=CENT)
    assert orc.piso_acionado is False
    assert orc.sanity.status == "ok"
    assert orc.sanity.dentro_da_faixa is True


def test_paginas_extras_features_e_multiplicadores(catalogo_fake: Catalogo) -> None:
    """basico, 4 pag (+2 extra *5h), dobro, vh=100, features fixo+trab, urgencia+capital.

    horas_dev = 10 + 10 (paginas) + 10 (trab) = 30
    horas_total = 30 * 1.5 = 45
    subtotal_dev = 45 * 100 * 2.0 = 9000
    add-ons fixos = 500 (so 'fixo' tem preco_fixo)
    subtotal = 9500
    apos_ajustes = 9500 * 1.2 * 1.3 = 14820
    apos_margem = 14820 * 1.25 = 18525
    preco_final = 18525 / 0.8 = 23156.25
    """
    entrada = ProjetoInput(
        tipo="basico",
        paginas=4,
        nivel_design="dobro",
        senioridade="cem",
        funcionalidades=["fixo", "trab"],
        urgencia=True,
        localizacao_capital=True,
    )
    orc = calcular(entrada, catalogo_fake)

    assert orc.horas_dev == 30.0
    assert orc.horas_total == 45.0
    assert orc.subtotal_dev == pytest.approx(9000.0, abs=CENT)
    assert len(orc.addons) == 1
    assert orc.subtotal_addons == pytest.approx(500.0, abs=CENT)
    assert orc.subtotal == pytest.approx(9500.0, abs=CENT)
    assert orc.urgencia_pct == 0.2
    assert orc.localizacao_pct == 0.3
    assert orc.preco_final == pytest.approx(23156.25, abs=CENT)
    assert orc.sanity.status == "acima_faixa"


def test_valor_hora_por_meta_mensal(catalogo_fake: Catalogo) -> None:
    """meta_mensal / horas_faturaveis define o valor/hora (regra Locaweb)."""
    entrada = ProjetoInput(
        tipo="basico",
        paginas=2,
        nivel_design="flat",
        senioridade="cem",
        meta_mensal=8000,
        horas_faturaveis_mes=160,
    )
    orc = calcular(entrada, catalogo_fake)
    assert orc.valor_hora == pytest.approx(50.0, abs=CENT)


def test_override_valor_hora_tem_prioridade(catalogo_fake: Catalogo) -> None:
    """valor_hora explicito vence meta_mensal e senioridade."""
    entrada = ProjetoInput(
        tipo="basico",
        nivel_design="flat",
        senioridade="cem",
        valor_hora=123.0,
        meta_mensal=8000,
    )
    orc = calcular(entrada, catalogo_fake)
    assert orc.valor_hora == 123.0


def test_piso_e_acionado_quando_preco_abaixo(catalogo_fake: Catalogo) -> None:
    """valor/hora irrisorio => preco abaixo do piso => elevado ao piso."""
    entrada = ProjetoInput(
        tipo="basico", paginas=2, nivel_design="flat", senioridade="cem", valor_hora=1.0
    )
    orc = calcular(entrada, catalogo_fake)
    assert orc.piso_acionado is True
    assert orc.preco_final == pytest.approx(1000.0, abs=CENT)  # piso do tipo basico
    assert orc.sanity.status == "abaixo_piso"
    assert orc.sanity.abaixo_do_piso is True


def test_funcionalidade_duplicada_nao_cobra_duas_vezes(catalogo_fake: Catalogo) -> None:
    entrada = ProjetoInput(
        tipo="basico", nivel_design="flat", senioridade="cem", funcionalidades=["fixo", "fixo"]
    )
    orc = calcular(entrada, catalogo_fake)
    assert len(orc.addons) == 1
    assert orc.subtotal_addons == pytest.approx(500.0, abs=CENT)


def test_recorrentes_hospedagem_dominio_manutencao(catalogo_fake: Catalogo) -> None:
    entrada = ProjetoInput(
        tipo="basico",
        nivel_design="flat",
        senioridade="cem",
        hospedagem="vps",
        incluir_dominio=True,
        manutencao_mensal=200,
    )
    orc = calcular(entrada, catalogo_fake)
    descricoes = [r.descricao for r in orc.recorrentes]
    assert any("Hospedagem" in d for d in descricoes)
    assert any("Dominio" in d for d in descricoes)
    assert any("Manutencao" in d for d in descricoes)
    # hospedagem 50/mes + manutencao 200/mes = 250/mes (dominio e anual)
    assert orc.total_recorrente_mensal == pytest.approx(250.0, abs=CENT)


def test_tipo_inexistente_levanta_erro(catalogo_fake: Catalogo) -> None:
    entrada = ProjetoInput(tipo="nao_existe", nivel_design="flat", senioridade="cem")
    with pytest.raises(PrecificacaoError, match="tipo de site inexistente"):
        calcular(entrada, catalogo_fake)


def test_funcionalidade_inexistente_levanta_erro(catalogo_fake: Catalogo) -> None:
    entrada = ProjetoInput(
        tipo="basico", nivel_design="flat", senioridade="cem", funcionalidades=["fantasma"]
    )
    with pytest.raises(PrecificacaoError, match="funcionalidade"):
        calcular(entrada, catalogo_fake)


def test_design_inexistente_levanta_erro(catalogo_fake: Catalogo) -> None:
    entrada = ProjetoInput(tipo="basico", nivel_design="nao_existe", senioridade="cem")
    with pytest.raises(PrecificacaoError, match="design inexistente"):
        calcular(entrada, catalogo_fake)


def test_senioridade_inexistente_levanta_erro(catalogo_fake: Catalogo) -> None:
    entrada = ProjetoInput(tipo="basico", nivel_design="flat", senioridade="nao_existe")
    with pytest.raises(PrecificacaoError, match="senioridade inexistente"):
        calcular(entrada, catalogo_fake)


def test_hospedagem_inexistente_levanta_erro(catalogo_fake: Catalogo) -> None:
    entrada = ProjetoInput(
        tipo="basico", nivel_design="flat", senioridade="cem", hospedagem="nao_existe"
    )
    with pytest.raises(PrecificacaoError, match="hospedagem inexistente"):
        calcular(entrada, catalogo_fake)


def test_status_abaixo_faixa(catalogo_fake: Catalogo) -> None:
    """Preco acima do piso porem abaixo da faixa de mercado -> alerta de subprecificacao."""
    entrada = ProjetoInput(tipo="faixa_alta", paginas=2, nivel_design="flat", senioridade="cem")
    orc = calcular(entrada, catalogo_fake)
    assert orc.piso_acionado is False
    assert orc.sanity.status == "abaixo_faixa"
    assert orc.sanity.dentro_da_faixa is False


def test_determinismo(catalogo_fake: Catalogo) -> None:
    """Mesma entrada => saida identica (exceto a data, que e 'hoje')."""
    entrada = ProjetoInput(
        tipo="basico",
        paginas=5,
        nivel_design="dobro",
        senioridade="cem",
        funcionalidades=["fixo", "trab"],
        urgencia=True,
    )
    a = calcular(entrada, catalogo_fake).model_dump()
    b = calcular(entrada, catalogo_fake).model_dump()
    assert a == b
