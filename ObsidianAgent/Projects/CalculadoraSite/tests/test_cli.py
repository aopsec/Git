"""Testes do modo nao interativo (Typer CliRunner)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from calculadora_site.cli import app

runner = CliRunner()


def test_listar_mostra_slugs() -> None:
    resultado = runner.invoke(app, ["listar"])
    assert resultado.exit_code == 0
    assert "institucional_simples" in resultado.output
    assert "template" in resultado.output


def test_calcular_tabela() -> None:
    resultado = runner.invoke(
        app, ["calcular", "-t", "institucional_simples", "-p", "5", "-s", "iniciante"]
    )
    assert resultado.exit_code == 0
    assert "PRECO FINAL" in resultado.output


def test_calcular_exporta_json_e_pdf(tmp_path: Path) -> None:
    base = tmp_path / "saida"
    resultado = runner.invoke(
        app,
        [
            "calcular",
            "-t", "landing_simples",
            "-f", "seo_basico",
            "-o", "json",
            "-o", "pdf",
            "--out-file", str(base),
        ],
    )
    assert resultado.exit_code == 0
    assert base.with_suffix(".json").exists()
    pdf = base.with_suffix(".pdf")
    assert pdf.exists()
    assert pdf.read_bytes().startswith(b"%PDF")


def test_calcular_tipo_invalido_sai_com_erro() -> None:
    resultado = runner.invoke(app, ["calcular", "-t", "nao_existe"])
    assert resultado.exit_code == 2


def test_calcular_funcionalidade_invalida_sai_com_erro() -> None:
    resultado = runner.invoke(app, ["calcular", "-t", "landing_simples", "-f", "fantasma"])
    assert resultado.exit_code == 2


def test_formato_desconhecido_sai_com_erro() -> None:
    resultado = runner.invoke(app, ["calcular", "-t", "landing_simples", "-o", "docx"])
    assert resultado.exit_code == 2


def test_paginas_zero_rejeitado() -> None:
    resultado = runner.invoke(app, ["calcular", "-t", "landing_simples", "-p", "0"])
    assert resultado.exit_code != 0


def test_precos_inexistente_sai_com_erro(tmp_path: Path) -> None:
    resultado = runner.invoke(
        app, ["calcular", "-t", "landing_simples", "--precos", str(tmp_path / "x.yaml")]
    )
    assert resultado.exit_code == 2


def test_export_sem_out_file_usa_pasta_orcamentos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    resultado = runner.invoke(app, ["calcular", "-t", "landing_simples", "-o", "json"])
    assert resultado.exit_code == 0
    arquivos = list((tmp_path / "orcamentos").glob("orcamento_*.json"))
    assert len(arquivos) == 1


def test_sem_subcomando_abre_tui(monkeypatch) -> None:
    chamado = {"executou": False}

    def fake_executar() -> None:
        chamado["executou"] = True

    monkeypatch.setattr("calculadora_site.ui.tui_app.executar", fake_executar)
    resultado = runner.invoke(app, [])
    assert resultado.exit_code == 0
    assert chamado["executou"] is True
