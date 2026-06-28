"""Fixtures compartilhadas dos testes.

`catalogo_fake` e um catalogo sintetico com numeros redondos para provar a
FORMULA de forma independente dos dados de mercado. `catalogo_real` carrega o
``precos.yaml` embarcado, para testar os dados que de fato sao enviados.
"""

from __future__ import annotations

import pytest

from calculadora_site.core.catalog import carregar_catalogo
from calculadora_site.core.models import Catalogo

_FAKE: dict = {
    "meta": {"moeda": "BRL", "data_atualizacao": "2026-01-01", "aviso": "teste"},
    "parametros": {
        "overhead_pct": 0.5,
        "urgencia_pct": 0.2,
        "localizacao_capital_pct": 0.3,
        "margem_lucro_pct": 0.25,
        "carga_tributaria_pct": 0.2,
        "piso_minimo": 100.0,
        "dominio_anual": 40.0,
    },
    "tipos_site": {
        "basico": {
            "nome": "Basico",
            "horas_base": 10,
            "paginas_incluidas": 2,
            "horas_por_pagina_extra": 5,
            "piso": 1000.0,
            "faixa_mercado": [1000, 5000],
            "descricao": "tipo de teste",
        },
        # piso baixo + faixa alta: permite preco acima do piso porem abaixo da faixa.
        "faixa_alta": {
            "nome": "Faixa alta",
            "horas_base": 10,
            "paginas_incluidas": 2,
            "horas_por_pagina_extra": 5,
            "piso": 100.0,
            "faixa_mercado": [3000, 9000],
            "descricao": "testa status abaixo_faixa",
        },
    },
    "design": {
        "flat": {"nome": "Flat", "multiplicador": 1.0},
        "dobro": {"nome": "Dobro", "multiplicador": 2.0},
    },
    "senioridade": {
        "cem": {"nome": "Cem por hora", "valor_hora": 100.0},
    },
    "funcionalidades": {
        "fixo": {"nome": "Add-on fixo", "horas": 0, "preco_fixo": 500},
        "trab": {"nome": "Add-on trabalhoso", "horas": 10, "preco_fixo": 0},
    },
    "hospedagem": {
        "nenhuma": {"nome": "Nao incluir", "custo_mensal": 0},
        "vps": {"nome": "VPS", "custo_mensal": 50},
    },
}


@pytest.fixture
def catalogo_fake() -> Catalogo:
    return Catalogo.model_validate(_FAKE)


@pytest.fixture
def catalogo_real() -> Catalogo:
    return carregar_catalogo()
