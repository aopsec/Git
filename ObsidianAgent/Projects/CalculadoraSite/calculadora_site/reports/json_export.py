"""Exportacao do orcamento para JSON (auditavel / reprocessavel).

Saida deterministica: a ordem de campos segue a definicao do modelo pydantic e
o conteudo nao depende de locale. Mantido em paralelo aos relatorios humanos
(TXT/PDF) para que cada orcamento seja reproduzivel a partir do JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.models import Orcamento


def orcamento_para_dict(orcamento: Orcamento) -> dict[str, Any]:
    """Modelo -> dict serializavel (numeros como float, sem objetos pydantic)."""
    return orcamento.model_dump(mode="json")


def orcamento_para_json(orcamento: Orcamento) -> str:
    """Modelo -> string JSON identada, UTF-8, acentos preservados."""
    return json.dumps(orcamento_para_dict(orcamento), ensure_ascii=False, indent=2)


def exportar_json(orcamento: Orcamento, caminho: Path | str) -> Path:
    """Grava o orcamento em ``caminho`` e devolve o Path final."""
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(orcamento_para_json(orcamento) + "\n", encoding="utf-8")
    return destino
