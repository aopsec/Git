"""Interface de linha de comando (Typer).

Sem subcomando -> abre a TUI (modo interativo). Com ``calcular`` -> modo nao
interativo (flags), util para automacao/scripts. ``listar`` mostra os slugs
disponiveis no catalogo.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from .core.catalog import CatalogoError, carregar_catalogo
from .core.models import Catalogo, Orcamento, ProjetoInput
from .core.pricing import PrecificacaoError
from .core.pricing import calcular as motor_calcular
from .reports import exportar_json, exportar_txt, gerar_pdf
from .ui import theme
from .ui.render import painel_orcamento

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="ADVAN7Tech - Calculadora de precificacao de sites (mercado BR 2026).",
)
console = Console()

FORMATOS_ARQUIVO = {"pdf", "json", "txt"}


@app.callback(invoke_without_command=True)
def _principal(ctx: typer.Context) -> None:
    """Sem subcomando, abre a interface interativa (TUI)."""
    if ctx.invoked_subcommand is None:
        from .ui.tui_app import executar

        executar()


def _carregar(precos: Path | None) -> Catalogo:
    try:
        return carregar_catalogo(precos)
    except CatalogoError as exc:
        typer.secho(f"Erro no catalogo de precos: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc


def _resolver_saida(out_file: Path | None, orcamento: Orcamento, ext: str) -> Path:
    if out_file is not None:
        return out_file.with_suffix(f".{ext}")
    nome = orcamento.cliente or orcamento.tipo_slug
    slug = "".join(c if c.isalnum() else "-" for c in nome).strip("-").lower() or "orcamento"
    return Path.cwd() / "orcamentos" / f"orcamento_{slug}_{date.today().isoformat()}.{ext}"


@app.command()
def calcular(
    tipo: str = typer.Option(..., "--tipo", "-t", help="Slug do tipo de site (ver 'listar')."),
    paginas: int = typer.Option(1, "--paginas", "-p", min=1),
    design: str = typer.Option("template", "--design", "-d"),
    senioridade: str = typer.Option("pleno", "--senioridade", "-s"),
    valor_hora: float | None = typer.Option(None, "--valor-hora", help="Sobrescreve o valor/hora."),
    meta_mensal: float | None = typer.Option(None, "--meta-mensal", help="Meta liquida -> valor/hora."),
    funcionalidade: list[str] = typer.Option(
        [], "--funcionalidade", "-f", help="Slug de add-on (repetivel)."
    ),
    urgencia: bool = typer.Option(False, "--urgencia/--sem-urgencia"),
    capital: bool = typer.Option(False, "--capital/--sem-capital"),
    margem: float | None = typer.Option(None, "--margem", help="Fracao, ex.: 0.3 = 30%."),
    tributo: float | None = typer.Option(None, "--tributo", help="Fracao < 1, ex.: 0.06."),
    desconto: float | None = typer.Option(
        None, "--desconto", help="Desconto comercial ao cliente, fracao < 1 (ex.: 0.15)."
    ),
    arredondar: bool = typer.Option(
        False, "--arredondar/--sem-arredondar", help="Arredonda o preco final a um numero atrativo."
    ),
    hospedagem: str = typer.Option("nenhuma", "--hospedagem"),
    dominio: bool = typer.Option(False, "--dominio/--sem-dominio"),
    manutencao: float = typer.Option(0.0, "--manutencao", min=0.0),
    cliente: str = typer.Option("", "--cliente"),
    projeto: str = typer.Option("", "--projeto"),
    output: list[str] = typer.Option(
        ["tabela"], "--output", "-o", help="tabela|pdf|json|txt (repetivel)."
    ),
    out_file: Path | None = typer.Option(None, "--out-file", help="Caminho base de saida."),
    precos: Path | None = typer.Option(None, "--precos", help="precos.yaml alternativo."),
) -> None:
    """Calcula um orcamento por flags (modo nao interativo)."""
    catalogo = _carregar(precos)
    try:
        entrada = ProjetoInput(
            tipo=tipo,
            paginas=paginas,
            nivel_design=design,
            senioridade=senioridade,
            funcionalidades=funcionalidade,
            valor_hora=valor_hora,
            meta_mensal=meta_mensal,
            urgencia=urgencia,
            localizacao_capital=capital,
            margem_lucro_pct=margem,
            carga_tributaria_pct=tributo,
            desconto_pct=desconto,
            arredondar=arredondar,
            hospedagem=hospedagem,
            incluir_dominio=dominio,
            manutencao_mensal=manutencao,
            cliente=cliente,
            projeto=projeto,
        )
        orcamento = motor_calcular(entrada, catalogo)
    except (ValidationError, PrecificacaoError, ValueError) as exc:
        typer.secho(f"Erro de entrada: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    for fmt in output:
        if fmt == "tabela":
            console.print(painel_orcamento(orcamento))
        elif fmt in FORMATOS_ARQUIVO:
            destino = _resolver_saida(out_file, orcamento, fmt)
            if fmt == "pdf":
                gerar_pdf(orcamento, destino)
            elif fmt == "json":
                exportar_json(orcamento, destino)
            else:
                exportar_txt(orcamento, destino)
            typer.secho(f"[{fmt}] salvo em {destino}", fg=typer.colors.GREEN)
        else:
            typer.secho(
                f"Formato desconhecido: {fmt!r} (use tabela|pdf|json|txt).",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(2)


@app.command()
def listar(precos: Path | None = typer.Option(None, "--precos", help="precos.yaml alternativo.")) -> None:
    """Lista os slugs disponiveis no catalogo (tipos, design, etc.)."""
    catalogo = _carregar(precos)
    grupos: list[tuple[str, dict[str, str]]] = [
        ("Tipos de site (--tipo)", {s: v.nome for s, v in catalogo.tipos_site.items()}),
        ("Design (--design)", {s: v.nome for s, v in catalogo.design.items()}),
        ("Senioridade (--senioridade)", {s: v.nome for s, v in catalogo.senioridade.items()}),
        ("Funcionalidades (--funcionalidade)", {s: v.nome for s, v in catalogo.funcionalidades.items()}),
        ("Hospedagem (--hospedagem)", {s: v.nome for s, v in catalogo.hospedagem.items()}),
    ]
    for titulo, itens in grupos:
        tabela = Table(title=titulo, title_justify="left", border_style=theme.TEXTO_SUAVE)
        tabela.add_column("slug", style=theme.ACENTO)
        tabela.add_column("nome")
        for slug, nome in itens.items():
            tabela.add_row(slug, nome)
        console.print(tabela)


def main() -> None:
    """Entry point do console script ``calculadora-site``."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
