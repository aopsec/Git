"""Carregamento e validacao do catalogo de precos (``config/precos.yaml``).

Mantem a leitura de disco isolada do motor: o motor recebe um :class:`Catalogo`
ja validado e nunca toca em arquivos. Todos os modos de falha de I/O e parsing
viram uma unica :class:`CatalogoError` com mensagem acionavel.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import Catalogo


class CatalogoError(Exception):
    """Falha ao localizar, ler, parsear ou validar o catalogo de precos."""


def caminho_padrao() -> Path:
    """``calculadora_site/config/precos.yaml`` (relativo ao pacote)."""
    return Path(__file__).resolve().parent.parent / "config" / "precos.yaml"


def carregar_catalogo(caminho: Path | str | None = None) -> Catalogo:
    """Le e valida o catalogo. ``caminho=None`` usa :func:`caminho_padrao`.

    Levanta :class:`CatalogoError` para arquivo ausente, YAML invalido,
    estrutura inesperada ou violacao de schema.
    """
    alvo = Path(caminho) if caminho is not None else caminho_padrao()

    if not alvo.exists():
        raise CatalogoError(f"arquivo de precos nao encontrado: {alvo}")
    if not alvo.is_file():
        raise CatalogoError(f"caminho de precos nao e um arquivo: {alvo}")

    try:
        texto = alvo.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogoError(f"falha ao ler {alvo}: {exc}") from exc

    try:
        bruto = yaml.safe_load(texto)
    except yaml.YAMLError as exc:
        raise CatalogoError(f"YAML invalido em {alvo}: {exc}") from exc

    if not isinstance(bruto, dict):
        raise CatalogoError(f"o catalogo em {alvo} deve ser um mapeamento (dict) no topo")

    try:
        return Catalogo.model_validate(bruto)
    except ValidationError as exc:
        raise CatalogoError(f"catalogo invalido em {alvo}:\n{exc}") from exc
