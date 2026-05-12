"""Build planning for the unified ADV7Sec 1.0 runtime."""

from __future__ import annotations

from adv7sec_1_0 import __version__
from adv7sec_1_0.models import BuildPlan, BuildStep, Finding, RuntimeTarget


def build_plan(target: RuntimeTarget, findings: list[Finding]) -> BuildPlan:
    """Return the staged plan for the unified Linux-first version."""
    blockers = [finding.title for finding in findings if finding.severity in {"critical", "high"}]
    return BuildPlan(
        version=__version__,
        target=target,
        goals=[
            "Unificar install, audit, monitor, response e doctor em um unico entrypoint Python.",
            "Operar em Arch, Debian/Ubuntu e Fedora por adapters de pacote e service names.",
            "Fornecer live logs, live auto-audit e resposta segura com dry-run por padrao.",
        ],
        blockers=blockers,
        runtime_layout=[
            "ADV7Sec_1.0v.py",
            "adv7sec_1_0/",
            ".vendor/",
        ],
        cleanup_after_parity=[],
        steps=[
            BuildStep(
                id="PLAN-01",
                title="Core Linux target",
                objective=(
                    "Detectar distro, init, package manager, services "
                    "e adapters de install em runtime."
                ),
            ),
            BuildStep(
                id="PLAN-02",
                title="Unified UX",
                objective=(
                    "Expor CLI user-friendly com audit, plan, doctor, backend, "
                    "install, monitor, analyze, respond e smoke."
                ),
            ),
            BuildStep(
                id="PLAN-03",
                title="Packaged resources",
                objective=(
                    "Ler configs e helpers via importlib.resources "
                    "para remover a dependencia do layout legado."
                ),
            ),
            BuildStep(
                id="PLAN-04",
                title="Live pipeline",
                objective=(
                    "Mapear journald e arquivos locais para "
                    "eventos normalizados, auto-audit e consulta rapida."
                ),
            ),
            BuildStep(
                id="PLAN-05",
                title="Safe response",
                objective=(
                    "Introduzir respostas seguras derivadas de analise, "
                    "com preview e --execute explicito."
                ),
            ),
            BuildStep(
                id="PLAN-06",
                title="Runtime hygiene",
                objective=(
                    "Manter apenas o runtime ativo, recursos empacotados "
                    "e gates Python estritos."
                ),
            ),
        ],
    )
