#!/usr/bin/env python3
"""CalculadoraSite.py — launcher do pacote ``calculadora_site``.

Permite rodar a ferramenta direto do diretorio do projeto, sem instalar::

    python CalculadoraSite.py                 # abre a TUI (modo interativo)
    python CalculadoraSite.py listar          # lista os slugs do catalogo
    python CalculadoraSite.py calcular -t institucional_simples -p 5 -o pdf

Equivale ao console script ``calculadora-site`` (ver pyproject.toml).
"""

from __future__ import annotations

from calculadora_site.cli import main

if __name__ == "__main__":
    main()
