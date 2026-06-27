"""Motor de calculo de precificacao - PURO, sem I/O.

Esta e a fonte da verdade da formula. Recebe um :class:`ProjetoInput` validado e
um :class:`Catalogo` carregado, devolve um :class:`Orcamento` serializavel. Nao
le arquivos, nao imprime, nao tem efeitos colaterais - o que o torna trivialmente
testavel e deterministico (mesma entrada => mesma saida byte-a-byte).

Formula consolidada (todas as % vem do catalogo, sobrescritiveis por projeto)::

    horas_dev    = horas_base_tipo + paginas_extra * h/pag + Sigma horas_features
    horas_total  = horas_dev * (1 + overhead%)
    subtotal_dev = horas_total * valor_hora * mult_design
    subtotal     = subtotal_dev + Sigma add_ons_fixos
    apos_ajustes = subtotal * (1 + urgencia%) * (1 + localizacao%)
    apos_margem  = apos_ajustes * (1 + margem_lucro%)
    preco_final  = apos_margem / (1 - carga_tributaria%)
    preco_final  = max(preco_final, piso_projeto)

A senioridade NAO entra como multiplicador: ela define o ``valor_hora`` sugerido
(evita dupla contagem, ja que as faixas de valor/hora ja embutem senioridade).

Custos recorrentes (hospedagem, dominio, manutencao) sao listados a parte e nao
entram no ``preco_final``.
"""

from __future__ import annotations

from datetime import date

from ..formatting import formatar_brl
from .models import (
    Catalogo,
    Funcionalidade,
    Hospedagem,
    LinhaItem,
    Orcamento,
    ProjetoInput,
    Recorrente,
    SanityCheck,
    TipoSite,
)


class PrecificacaoError(ValueError):
    """Erro de dominio do motor: slug inexistente, parametro fora do dominio."""


def _dinheiro(valor: float) -> float:
    """Arredonda para centavos de forma deterministica."""
    return round(valor, 2)


def _horas(valor: float) -> float:
    return round(valor, 2)


def _resolver_valor_hora(entrada: ProjetoInput, valor_hora_senioridade: float) -> float:
    """Prioridade: override direto > meta mensal / horas faturaveis > senioridade."""
    if entrada.valor_hora is not None:
        return entrada.valor_hora
    if entrada.meta_mensal is not None:
        # horas_faturaveis_mes > 0 garantido pelo modelo (Field gt=0).
        return entrada.meta_mensal / entrada.horas_faturaveis_mes
    return valor_hora_senioridade


def _validar_funcionalidades(entrada: ProjetoInput, catalogo: Catalogo) -> list[Funcionalidade]:
    desconhecidas = [f for f in entrada.funcionalidades if f not in catalogo.funcionalidades]
    if desconhecidas:
        disponiveis = ", ".join(sorted(catalogo.funcionalidades))
        raise PrecificacaoError(
            f"funcionalidade(s) inexistente(s): {', '.join(desconhecidas)}. "
            f"Disponiveis: {disponiveis}"
        )
    # Preserva a ordem de entrada, mas remove duplicatas para nao cobrar duas vezes.
    vistos: dict[str, Funcionalidade] = {}
    for slug in entrada.funcionalidades:
        vistos.setdefault(slug, catalogo.funcionalidades[slug])
    return list(vistos.values())


def _montar_itens_escopo(
    tipo: TipoSite,
    paginas_extra: int,
    horas_paginas: float,
    funcionalidades: list[Funcionalidade],
) -> list[LinhaItem]:
    """Linhas de horas para o detalhamento do relatorio."""
    itens = [LinhaItem(descricao=f"Base: {tipo.nome}", horas=_horas(tipo.horas_base))]
    if horas_paginas > 0:
        itens.append(
            LinhaItem(
                descricao=f"Paginas extras ({paginas_extra} x {tipo.horas_por_pagina_extra}h)",
                horas=_horas(horas_paginas),
            )
        )
    itens.extend(
        LinhaItem(descricao=f"Funcionalidade: {f.nome}", horas=_horas(f.horas))
        for f in funcionalidades
        if f.horas > 0
    )
    return itens


def _montar_recorrentes(
    entrada: ProjetoInput, hospedagem: Hospedagem, dominio_anual: float
) -> list[Recorrente]:
    """Custos recorrentes (listados a parte do preco do projeto)."""
    recorrentes: list[Recorrente] = []
    if hospedagem.custo_mensal > 0:
        recorrentes.append(
            Recorrente(
                descricao=f"Hospedagem ({hospedagem.nome})",
                valor_mensal=_dinheiro(hospedagem.custo_mensal),
                valor_anual=_dinheiro(hospedagem.custo_mensal * 12),
            )
        )
    if entrada.incluir_dominio:
        recorrentes.append(
            Recorrente(
                descricao="Dominio .com.br (Registro.br)",
                valor_mensal=0.0,
                valor_anual=_dinheiro(dominio_anual),
            )
        )
    if entrada.manutencao_mensal > 0:
        recorrentes.append(
            Recorrente(
                descricao="Manutencao mensal",
                valor_mensal=_dinheiro(entrada.manutencao_mensal),
                valor_anual=_dinheiro(entrada.manutencao_mensal * 12),
            )
        )
    return recorrentes


def calcular(entrada: ProjetoInput, catalogo: Catalogo) -> Orcamento:
    """Calcula o orcamento. Levanta :class:`PrecificacaoError` para entradas
    coerentes com o schema mas invalidas no dominio (ex.: tipo inexistente)."""

    # --- 1. resolver entidades do catalogo ------------------------------------
    tipo = catalogo.tipos_site.get(entrada.tipo)
    if tipo is None:
        raise PrecificacaoError(
            f"tipo de site inexistente: {entrada.tipo!r}. "
            f"Disponiveis: {', '.join(sorted(catalogo.tipos_site))}"
        )
    design = catalogo.design.get(entrada.nivel_design)
    if design is None:
        raise PrecificacaoError(
            f"nivel de design inexistente: {entrada.nivel_design!r}. "
            f"Disponiveis: {', '.join(sorted(catalogo.design))}"
        )
    senioridade = catalogo.senioridade.get(entrada.senioridade)
    if senioridade is None:
        raise PrecificacaoError(
            f"senioridade inexistente: {entrada.senioridade!r}. "
            f"Disponiveis: {', '.join(sorted(catalogo.senioridade))}"
        )
    hospedagem = catalogo.hospedagem.get(entrada.hospedagem)
    if hospedagem is None:
        raise PrecificacaoError(
            f"hospedagem inexistente: {entrada.hospedagem!r}. "
            f"Disponiveis: {', '.join(sorted(catalogo.hospedagem))}"
        )
    funcionalidades = _validar_funcionalidades(entrada, catalogo)

    params = catalogo.parametros

    # parametros com possivel override por projeto
    overhead_pct = entrada.overhead_pct if entrada.overhead_pct is not None else params.overhead_pct
    margem_pct = (
        entrada.margem_lucro_pct if entrada.margem_lucro_pct is not None else params.margem_lucro_pct
    )
    tributo_pct = (
        entrada.carga_tributaria_pct
        if entrada.carga_tributaria_pct is not None
        else params.carga_tributaria_pct
    )
    # Defesa em profundidade: o schema ja garante < 1, mas o divisor e critico.
    if tributo_pct >= 1:  # pragma: no cover - inalcancavel via modelo validado
        raise PrecificacaoError("carga_tributaria_pct deve ser < 1 (entra como divisor)")

    valor_hora = _resolver_valor_hora(entrada, senioridade.valor_hora)
    if valor_hora <= 0:  # pragma: no cover - todas as fontes de valor/hora sao > 0
        raise PrecificacaoError("valor/hora resolvido deve ser > 0")

    # --- 2. horas -------------------------------------------------------------
    paginas_extra = max(0, entrada.paginas - tipo.paginas_incluidas)
    horas_paginas = paginas_extra * tipo.horas_por_pagina_extra
    horas_features = sum(f.horas for f in funcionalidades)
    horas_dev = tipo.horas_base + horas_paginas + horas_features
    horas_overhead = horas_dev * overhead_pct
    horas_total = horas_dev + horas_overhead

    # --- 3. subtotais ---------------------------------------------------------
    subtotal_dev = horas_total * valor_hora * design.multiplicador

    addons = [
        LinhaItem(descricao=f.nome, valor=_dinheiro(f.preco_fixo))
        for f in funcionalidades
        if f.preco_fixo > 0
    ]
    subtotal_addons = sum(item.valor for item in addons)
    subtotal = subtotal_dev + subtotal_addons

    # --- 4. ajustes finais ----------------------------------------------------
    urgencia_pct = params.urgencia_pct if entrada.urgencia else 0.0
    localizacao_pct = params.localizacao_capital_pct if entrada.localizacao_capital else 0.0

    preco_apos_ajustes = subtotal * (1 + urgencia_pct) * (1 + localizacao_pct)
    preco_apos_margem = preco_apos_ajustes * (1 + margem_pct)
    preco_final = preco_apos_margem / (1 - tributo_pct)

    piso = max(tipo.piso, params.piso_minimo)
    piso_acionado = preco_final < piso
    if piso_acionado:
        preco_final = piso

    # --- 5. sanity check contra a faixa de mercado ----------------------------
    sanity = _avaliar_faixa(preco_final, tipo.faixa_mercado, piso_acionado)

    # --- 6. itens de escopo (detalhamento de horas para o relatorio) ----------
    itens_escopo = _montar_itens_escopo(tipo, paginas_extra, horas_paginas, funcionalidades)

    # --- 7. custos recorrentes ------------------------------------------------
    recorrentes = _montar_recorrentes(entrada, hospedagem, params.dominio_anual)
    total_recorrente_mensal = sum(r.valor_mensal for r in recorrentes)

    # --- 8. montar o orcamento ------------------------------------------------
    return Orcamento(
        cliente=entrada.cliente,
        projeto=entrada.projeto,
        data=date.today().isoformat(),
        validade_dias=entrada.validade_dias,
        tipo_slug=entrada.tipo,
        tipo_nome=tipo.nome,
        moeda=catalogo.meta.moeda,
        data_tabela=catalogo.meta.data_atualizacao,
        aviso=catalogo.meta.aviso,
        horas_dev=_horas(horas_dev),
        horas_overhead=_horas(horas_overhead),
        horas_total=_horas(horas_total),
        valor_hora=_dinheiro(valor_hora),
        overhead_pct=overhead_pct,
        mult_design=design.multiplicador,
        subtotal_dev=_dinheiro(subtotal_dev),
        addons=addons,
        subtotal_addons=_dinheiro(subtotal_addons),
        subtotal=_dinheiro(subtotal),
        urgencia_pct=urgencia_pct,
        localizacao_pct=localizacao_pct,
        margem_lucro_pct=margem_pct,
        carga_tributaria_pct=tributo_pct,
        preco_apos_ajustes=_dinheiro(preco_apos_ajustes),
        preco_apos_margem=_dinheiro(preco_apos_margem),
        preco_final=_dinheiro(preco_final),
        piso_aplicado=_dinheiro(piso),
        piso_acionado=piso_acionado,
        itens_escopo=itens_escopo,
        recorrentes=recorrentes,
        total_recorrente_mensal=_dinheiro(total_recorrente_mensal),
        sanity=sanity,
    )


def _avaliar_faixa(
    preco_final: float, faixa: tuple[float, float], piso_acionado: bool
) -> SanityCheck:
    """Classifica o preco final ante a faixa de mercado de referencia."""
    faixa_min, faixa_max = faixa
    dentro = faixa_min <= preco_final <= faixa_max

    faixa_txt = f"{formatar_brl(faixa_min, centavos=False)} a {formatar_brl(faixa_max, centavos=False)}"
    if piso_acionado:
        status = "abaixo_piso"
        mensagem = (
            "Preco elevado ao piso minimo do projeto. O escopo informado fica "
            "abaixo do minimo viavel - revise horas ou valor/hora."
        )
    elif preco_final < faixa_min:
        status = "abaixo_faixa"
        mensagem = (
            f"Abaixo da faixa de mercado ({faixa_txt}). "
            "Risco de subprecificacao: projetos 30-40% abaixo do mercado tendem a "
            "estourar o orcamento. Considere revisar."
        )
    elif preco_final > faixa_max:
        status = "acima_faixa"
        mensagem = (
            f"Acima da faixa tipica ({faixa_txt}). "
            "Coerente para escopo premium/complexo - confirme o valor percebido."
        )
    else:
        status = "ok"
        mensagem = f"Dentro da faixa de mercado ({faixa_txt})."

    return SanityCheck(
        faixa_min=faixa_min,
        faixa_max=faixa_max,
        dentro_da_faixa=dentro,
        abaixo_do_piso=piso_acionado,
        status=status,
        mensagem=mensagem,
    )
