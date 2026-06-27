"""Modelos de dominio da CalculadoraSite (pydantic v2).

Tres grupos:

* **Catalogo** e seus componentes — espelham `config/precos.yaml`. Sao validados
  com ``extra="forbid"`` para que um typo na YAML falhe alto, em vez de virar um
  campo silenciosamente ignorado.
* **ProjetoInput** — tudo que a UI/CLI coleta do usuario. Validacao de tipos e
  faixas acontece aqui; a validacao de *slugs* (existir no catalogo) acontece no
  motor (:mod:`calculadora_site.core.pricing`), que e quem conhece o catalogo.
* **Orcamento** e linhas — a saida pura e serializavel do motor, consumida pelos
  relatorios (PDF/JSON/TXT) sem recalcular nada.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    """Base que rejeita campos desconhecidos (pega typos na YAML/entrada)."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Catalogo (espelha precos.yaml)
# --------------------------------------------------------------------------- #
class MetaCatalogo(_Strict):
    moeda: str = "BRL"
    data_atualizacao: str
    fonte: str = ""
    aviso: str = ""


class Parametros(_Strict):
    overhead_pct: float = Field(0.35, ge=0)
    urgencia_pct: float = Field(0.20, ge=0)
    localizacao_capital_pct: float = Field(0.30, ge=0)
    margem_lucro_pct: float = Field(0.30, ge=0)
    # < 1 obrigatorio: entra como divisor no gross-up tributario.
    carga_tributaria_pct: float = Field(0.06, ge=0, lt=1)
    piso_minimo: float = Field(50.0, ge=0)
    dominio_anual: float = Field(40.0, ge=0)


class TipoSite(_Strict):
    nome: str
    horas_base: float = Field(ge=0)
    paginas_incluidas: int = Field(ge=1)
    horas_por_pagina_extra: float = Field(ge=0)
    piso: float = Field(ge=0)
    faixa_mercado: tuple[float, float]
    descricao: str = ""

    @model_validator(mode="after")
    def _faixa_coerente(self) -> TipoSite:
        baixo, alto = self.faixa_mercado
        if baixo < 0 or alto < 0:
            raise ValueError("faixa_mercado nao pode ter valores negativos")
        if baixo > alto:
            raise ValueError(f"faixa_mercado invertida: {baixo} > {alto}")
        return self


class NivelDesign(_Strict):
    nome: str
    multiplicador: float = Field(gt=0)
    descricao: str = ""


class Senioridade(_Strict):
    nome: str
    valor_hora: float = Field(gt=0)
    descricao: str = ""


class Funcionalidade(_Strict):
    nome: str
    categoria: str = "Funcionalidade"
    horas: float = Field(0, ge=0)
    preco_fixo: float = Field(0, ge=0)
    descricao: str = ""


class Hospedagem(_Strict):
    nome: str
    custo_mensal: float = Field(0, ge=0)


class Catalogo(_Strict):
    meta: MetaCatalogo
    parametros: Parametros
    tipos_site: dict[str, TipoSite]
    design: dict[str, NivelDesign]
    senioridade: dict[str, Senioridade]
    funcionalidades: dict[str, Funcionalidade]
    hospedagem: dict[str, Hospedagem]

    @model_validator(mode="after")
    def _nao_vazio(self) -> Catalogo:
        obrigatorios = {
            "tipos_site": self.tipos_site,
            "design": self.design,
            "senioridade": self.senioridade,
            "hospedagem": self.hospedagem,
        }
        vazios = [nome for nome, mapa in obrigatorios.items() if not mapa]
        if vazios:
            raise ValueError(f"secoes do catalogo nao podem ser vazias: {', '.join(vazios)}")
        return self


# --------------------------------------------------------------------------- #
# Entrada do usuario
# --------------------------------------------------------------------------- #
class ProjetoInput(_Strict):
    """Escopo + parametros comerciais coletados da UI/CLI.

    Slugs (``tipo``, ``nivel_design``, ``senioridade``, ``funcionalidades``,
    ``hospedagem``) sao validados contra o catalogo no motor de calculo, nao
    aqui — este modelo nao tem acesso ao catalogo.
    """

    # --- escopo ---
    tipo: str
    paginas: int = Field(1, ge=1)
    nivel_design: str = "template"
    senioridade: str = "pleno"
    funcionalidades: list[str] = Field(default_factory=list)

    # --- comercial ---
    # Prioridade do valor/hora: valor_hora > (meta_mensal / horas_faturaveis_mes)
    # > valor_hora sugerido da senioridade.
    valor_hora: float | None = Field(default=None, gt=0)
    meta_mensal: float | None = Field(default=None, gt=0)
    horas_faturaveis_mes: float = Field(default=100, gt=0)
    overhead_pct: float | None = Field(default=None, ge=0)
    urgencia: bool = False
    localizacao_capital: bool = False
    margem_lucro_pct: float | None = Field(default=None, ge=0)
    carga_tributaria_pct: float | None = Field(default=None, ge=0, lt=1)

    # --- recorrentes ---
    hospedagem: str = "nenhuma"
    incluir_dominio: bool = False
    manutencao_mensal: float = Field(default=0, ge=0)

    # --- metadados do orcamento ---
    cliente: str = ""
    projeto: str = ""
    validade_dias: int = Field(default=15, ge=1)


# --------------------------------------------------------------------------- #
# Saida (orcamento calculado)
# --------------------------------------------------------------------------- #
class LinhaItem(_Strict):
    descricao: str
    horas: float = 0.0
    valor: float = 0.0


class Recorrente(_Strict):
    descricao: str
    valor_mensal: float = 0.0
    valor_anual: float = 0.0


class SanityCheck(_Strict):
    """Comparacao do preco final com a faixa de mercado do tipo de site."""

    faixa_min: float
    faixa_max: float
    dentro_da_faixa: bool
    abaixo_do_piso: bool
    status: str  # "ok" | "abaixo_faixa" | "acima_faixa" | "abaixo_piso"
    mensagem: str


class Orcamento(_Strict):
    # metadados
    cliente: str
    projeto: str
    data: str
    validade_dias: int
    tipo_slug: str
    tipo_nome: str
    moeda: str
    data_tabela: str
    aviso: str

    # composicao de horas
    horas_dev: float
    horas_overhead: float
    horas_total: float
    valor_hora: float
    overhead_pct: float

    # subtotais
    mult_design: float
    subtotal_dev: float
    addons: list[LinhaItem]
    subtotal_addons: float
    subtotal: float

    # ajustes finais
    urgencia_pct: float
    localizacao_pct: float
    margem_lucro_pct: float
    carga_tributaria_pct: float
    preco_apos_ajustes: float
    preco_apos_margem: float
    preco_final: float
    piso_aplicado: float
    piso_acionado: bool

    # detalhamento para relatorio
    itens_escopo: list[LinhaItem]
    recorrentes: list[Recorrente]
    total_recorrente_mensal: float
    sanity: SanityCheck
