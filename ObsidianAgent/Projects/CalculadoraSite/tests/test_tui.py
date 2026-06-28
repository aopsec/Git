"""Smoke tests do app Textual via Pilot (sem terminal real).

Conduz o app com ``run_test()`` dentro de ``asyncio.run`` para nao depender do
plugin pytest-asyncio.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from pathlib import Path
from typing import TypeVar

from textual.widgets import Input, Select

from calculadora_site.core.catalog import carregar_catalogo
from calculadora_site.ui.tui_app import CalculadoraApp

T = TypeVar("T")


def _run(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)


def test_app_monta_e_calcula() -> None:
    catalogo = carregar_catalogo()

    async def cenario() -> None:
        app = CalculadoraApp(catalogo)
        async with app.run_test() as pilot:
            app.query_one("#tipo", Select).value = "institucional_simples"
            app.query_one("#paginas", Input).value = "5"
            app.query_one("#senioridade", Select).value = "iniciante"
            await pilot.pause()
            app.action_calcular()
            await pilot.pause()
            assert app._orcamento is not None
            assert app._orcamento.preco_final > 0
            assert app._orcamento.tipo_slug == "institucional_simples"

    _run(cenario())


def test_app_entrada_invalida_nao_quebra() -> None:
    catalogo = carregar_catalogo()

    async def cenario() -> None:
        app = CalculadoraApp(catalogo)
        async with app.run_test() as pilot:
            app.query_one("#paginas", Input).value = "0"  # viola paginas >= 1
            await pilot.pause()
            app.action_calcular()
            await pilot.pause()
            assert app._orcamento is None  # nao calculou, mas tambem nao quebrou

    _run(cenario())


def test_app_exporta_arquivos(tmp_path: Path) -> None:
    catalogo = carregar_catalogo()

    async def cenario() -> None:
        app = CalculadoraApp(catalogo)
        app.saida_dir = tmp_path
        async with app.run_test() as pilot:
            app.query_one("#tipo", Select).value = "landing_simples"
            await pilot.pause()
            app.action_calcular()
            await pilot.pause()
            app._exportar("json")
            app._exportar("pdf")
            app._exportar("txt")
            await pilot.pause()
            arquivos = list(tmp_path.glob("orcamento_*"))
            assert {p.suffix for p in arquivos} == {".json", ".pdf", ".txt"}

    _run(cenario())


def test_app_botoes_calcular_e_exportar(tmp_path: Path) -> None:
    """Exercita os handlers de botao (calcular + exportacoes) via cliques."""
    catalogo = carregar_catalogo()

    async def cenario() -> None:
        app = CalculadoraApp(catalogo)
        app.saida_dir = tmp_path
        async with app.run_test(size=(120, 50)) as pilot:
            app.query_one("#tipo", Select).value = "landing_simples"
            await pilot.pause()
            for botao in ("#btn_calcular", "#btn_pdf", "#btn_json", "#btn_txt"):
                app.query_one("#barra_acoes").scroll_visible(animate=False)
                await pilot.pause()
                await pilot.click(botao)
                await pilot.pause()
            assert app._orcamento is not None
            assert {p.suffix for p in tmp_path.glob("orcamento_*")} == {".json", ".pdf", ".txt"}

    _run(cenario())


def test_app_exportar_antes_de_calcular_avisa(tmp_path: Path) -> None:
    catalogo = carregar_catalogo()

    async def cenario() -> None:
        app = CalculadoraApp(catalogo)
        app.saida_dir = tmp_path
        async with app.run_test() as pilot:
            app._exportar("pdf")  # _orcamento ainda None -> apenas avisa
            await pilot.pause()
            assert list(tmp_path.glob("*")) == []

    _run(cenario())
