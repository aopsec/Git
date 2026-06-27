"""App Textual - wizard de precificacao em tela unica (formulario rolavel).

Coleta o escopo do projeto em secoes, calcula ao pressionar "Calcular" (ou F2)
e renderiza o orcamento no painel de resultado. Os botoes de exportacao geram
PDF (papel timbrado ADVAN7Tech) / JSON / TXT em ``./orcamentos/``.

A camada de apresentacao nao contem regra de negocio: ela apenas monta um
:class:`ProjetoInput`, chama o motor puro e formata a saida.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from pydantic import ValidationError
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    Select,
    SelectionList,
    Static,
)
from textual.widgets.selection_list import Selection

from ..core.catalog import carregar_catalogo
from ..core.models import Catalogo, Orcamento, ProjetoInput
from ..core.pricing import PrecificacaoError, calcular
from ..reports import exportar_json, exportar_txt, gerar_pdf
from . import theme
from .render import painel_orcamento


def _slug_arquivo(texto: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", texto.strip()).strip("-").lower()
    return base or "orcamento"


class CalculadoraApp(App[None]):
    """Calculadora de precificacao de sites - ADVAN7Tech."""

    CSS = theme.build_textual_css()
    TITLE = "ADVAN7Tech - Calculadora de Precificacao de Sites"
    BINDINGS = [
        ("f2", "calcular", "Calcular"),
        ("ctrl+q", "quit", "Sair"),
    ]

    def __init__(self, catalogo: Catalogo | None = None) -> None:
        super().__init__()
        self.catalogo = catalogo if catalogo is not None else carregar_catalogo()
        self._orcamento: Orcamento | None = None
        self.saida_dir = Path.cwd() / "orcamentos"

    # ------------------------------------------------------------------ layout
    def compose(self) -> ComposeResult:
        cat = self.catalogo
        yield Header()
        yield Static(f" {theme.MARCA.nome} - {theme.MARCA.documento} ", id="cabecalho")
        with VerticalScroll(id="corpo"):
            yield Label("Cliente", classes="rotulo")
            yield Input(placeholder="Nome do cliente", id="cliente")
            yield Label("Projeto", classes="rotulo")
            yield Input(placeholder="Nome do projeto", id="projeto")

            yield Label("Tipo de site", classes="rotulo")
            yield Select(
                [(t.nome, slug) for slug, t in cat.tipos_site.items()],
                value=next(iter(cat.tipos_site)),
                allow_blank=False,
                id="tipo",
            )
            yield Label("Numero de paginas", classes="rotulo")
            yield Input(value="1", type="integer", id="paginas")

            yield Label("Nivel de design", classes="rotulo")
            yield Select(
                [(d.nome, slug) for slug, d in cat.design.items()],
                value=next(iter(cat.design)),
                allow_blank=False,
                id="design",
            )

            yield Label("Senioridade (define valor/hora sugerido)", classes="rotulo")
            yield Select(
                [(f"{s.nome} - {theme.formatar_brl(s.valor_hora)}/h", slug)
                 for slug, s in cat.senioridade.items()],
                value="pleno" if "pleno" in cat.senioridade else next(iter(cat.senioridade)),
                allow_blank=False,
                id="senioridade",
            )
            yield Label("Valor/hora - sobrescreve (opcional)", classes="rotulo")
            yield Input(placeholder="ex.: 90", type="number", id="valor_hora")
            yield Label("Ou meta mensal liquida (opcional)", classes="rotulo")
            yield Input(placeholder="ex.: 7000 (÷ horas faturaveis)", type="number", id="meta_mensal")

            yield Label("Funcionalidades / add-ons", classes="rotulo")
            yield SelectionList[str](
                *[Selection(f"{f.nome} - {f.categoria}", slug)
                  for slug, f in cat.funcionalidades.items()],
                id="funcionalidades",
            )

            yield Checkbox("Projeto urgente (+urgencia)", id="urgencia")
            yield Checkbox("Cliente em capital / grande centro", id="capital")

            yield Label("Hospedagem (recorrente)", classes="rotulo")
            yield Select(
                [(h.nome, slug) for slug, h in cat.hospedagem.items()],
                value=next(iter(cat.hospedagem)),
                allow_blank=False,
                id="hospedagem",
            )
            yield Checkbox("Incluir dominio .com.br (R$ 40/ano)", id="dominio")
            yield Label("Manutencao mensal (R$, opcional)", classes="rotulo")
            yield Input(placeholder="ex.: 300", type="number", id="manutencao")

            with Horizontal(id="barra_acoes"):
                yield Button("Calcular (F2)", id="btn_calcular", classes="acao")
                yield Button("Exportar PDF", id="btn_pdf")
                yield Button("Exportar JSON", id="btn_json")
                yield Button("Exportar TXT", id="btn_txt")

            yield Static("Preencha o escopo e clique em Calcular.", id="painel_resultado")
        yield Footer()

    # ---------------------------------------------------------------- coleta
    def _input(self, id_: str) -> str:
        return self.query_one(f"#{id_}", Input).value.strip()

    def _num_opcional(self, id_: str) -> float | None:
        bruto = self._input(id_)
        if not bruto:
            return None
        return float(bruto.replace(",", "."))

    def _coletar_input(self) -> ProjetoInput:
        tipo = self.query_one("#tipo", Select).value
        design = self.query_one("#design", Select).value
        senior = self.query_one("#senioridade", Select).value
        hosp = self.query_one("#hospedagem", Select).value
        if Select.BLANK in (tipo, design, senior, hosp):
            raise ValueError("Selecione tipo, design, senioridade e hospedagem.")

        paginas_txt = self._input("paginas")
        funcs = list(self.query_one("#funcionalidades", SelectionList).selected)

        return ProjetoInput(
            tipo=str(tipo),
            paginas=int(paginas_txt) if paginas_txt else 1,
            nivel_design=str(design),
            senioridade=str(senior),
            funcionalidades=funcs,
            valor_hora=self._num_opcional("valor_hora"),
            meta_mensal=self._num_opcional("meta_mensal"),
            urgencia=self.query_one("#urgencia", Checkbox).value,
            localizacao_capital=self.query_one("#capital", Checkbox).value,
            hospedagem=str(hosp),
            incluir_dominio=self.query_one("#dominio", Checkbox).value,
            manutencao_mensal=self._num_opcional("manutencao") or 0.0,
            cliente=self._input("cliente"),
            projeto=self._input("projeto"),
        )

    # ---------------------------------------------------------------- acoes
    def action_calcular(self) -> None:
        try:
            entrada = self._coletar_input()
            orcamento = calcular(entrada, self.catalogo)
        except (ValidationError, PrecificacaoError, ValueError) as exc:
            self.notify(str(exc), title="Entrada invalida", severity="error", timeout=8)
            return
        self._orcamento = orcamento
        self.query_one("#painel_resultado", Static).update(painel_orcamento(orcamento))
        self.notify(
            f"Preco final: {theme.formatar_brl(orcamento.preco_final)}",
            title="Orcamento calculado",
        )

    def _caminho_saida(self, ext: str) -> Path:
        orc = self._orcamento
        assert orc is not None
        nome = _slug_arquivo(orc.cliente or orc.tipo_nome)
        return self.saida_dir / f"orcamento_{nome}_{date.today().isoformat()}.{ext}"

    def _exportar(self, formato: str) -> None:
        if self._orcamento is None:
            self.notify("Calcule o orcamento primeiro.", severity="warning")
            return
        destino = self._caminho_saida(formato)
        try:
            if formato == "pdf":
                gerar_pdf(self._orcamento, destino)
            elif formato == "json":
                exportar_json(self._orcamento, destino)
            else:
                exportar_txt(self._orcamento, destino)
        except OSError as exc:  # pragma: no cover - I/O dependente do ambiente
            self.notify(str(exc), title="Falha ao exportar", severity="error")
            return
        self.notify(f"Salvo: {destino}", title="Exportado")

    @on(Button.Pressed, "#btn_calcular")
    def _b_calcular(self) -> None:
        self.action_calcular()

    @on(Button.Pressed, "#btn_pdf")
    def _b_pdf(self) -> None:
        self._exportar("pdf")

    @on(Button.Pressed, "#btn_json")
    def _b_json(self) -> None:
        self._exportar("json")

    @on(Button.Pressed, "#btn_txt")
    def _b_txt(self) -> None:
        self._exportar("txt")


def executar(catalogo: Catalogo | None = None) -> None:  # pragma: no cover - requer TTY
    """Sobe o app Textual (modo interativo)."""
    CalculadoraApp(catalogo).run()
