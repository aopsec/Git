"""Testes de carregamento/validacao do catalogo e sanidade dos dados embarcados."""

from __future__ import annotations

from pathlib import Path

import pytest

from calculadora_site.core.catalog import CatalogoError, caminho_padrao, carregar_catalogo
from calculadora_site.core.models import Catalogo, ProjetoInput
from calculadora_site.core.pricing import calcular


def test_precos_embarcado_carrega(catalogo_real: Catalogo) -> None:
    assert catalogo_real.meta.moeda == "BRL"
    assert "institucional_simples" in catalogo_real.tipos_site
    assert "template" in catalogo_real.design
    assert "pleno" in catalogo_real.senioridade
    assert catalogo_real.parametros.carga_tributaria_pct < 1


def test_caminho_padrao_existe() -> None:
    assert caminho_padrao().is_file()


def test_arquivo_ausente_levanta_catalogo_error(tmp_path: Path) -> None:
    with pytest.raises(CatalogoError, match="nao encontrado"):
        carregar_catalogo(tmp_path / "inexistente.yaml")


def test_yaml_invalido_levanta_catalogo_error(tmp_path: Path) -> None:
    ruim = tmp_path / "ruim.yaml"
    ruim.write_text("isto: [nao, fecha", encoding="utf-8")
    with pytest.raises(CatalogoError, match="YAML invalido"):
        carregar_catalogo(ruim)


def test_yaml_nao_mapeamento_levanta_catalogo_error(tmp_path: Path) -> None:
    lista = tmp_path / "lista.yaml"
    lista.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(CatalogoError, match="mapeamento"):
        carregar_catalogo(lista)


def test_schema_invalido_levanta_catalogo_error(tmp_path: Path) -> None:
    """Campo extra desconhecido deve falhar (extra='forbid')."""
    ruim = tmp_path / "schema.yaml"
    ruim.write_text(
        "meta: {data_atualizacao: '2026-01-01'}\n"
        "parametros: {}\n"
        "tipos_site: {}\n"
        "design: {}\n"
        "senioridade: {}\n"
        "funcionalidades: {}\n"
        "hospedagem: {}\n"
        "campo_fantasma: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogoError, match="invalido"):
        carregar_catalogo(ruim)


@pytest.mark.parametrize(
    ("tipo", "senioridade"),
    [
        ("landing_simples", "iniciante"),
        ("institucional_simples", "iniciante"),
        ("institucional_completo", "pleno"),
        ("ecommerce_basico", "pleno"),
    ],
)
def test_config_representativa_fica_dentro_da_faixa(
    catalogo_real: Catalogo, tipo: str, senioridade: str
) -> None:
    """Configuracoes 'tipicas' (template, sem extras) devem cair na faixa de
    mercado do tipo — guarda de regressao dos dados embarcados."""
    paginas = catalogo_real.tipos_site[tipo].paginas_incluidas
    entrada = ProjetoInput(
        tipo=tipo, paginas=paginas, nivel_design="template", senioridade=senioridade
    )
    orc = calcular(entrada, catalogo_real)
    assert orc.sanity.dentro_da_faixa, (
        f"{tipo}/{senioridade}: R$ {orc.preco_final} fora de "
        f"[{orc.sanity.faixa_min}, {orc.sanity.faixa_max}]"
    )
