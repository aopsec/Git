"""Repository audit helpers for ADV7Sec 1.0."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from adv7sec_1_0.backends import build_backend_plan
from adv7sec_1_0.executor import execute_operation_plan
from adv7sec_1_0.install import apply_install_report, build_install_report
from adv7sec_1_0.models import Finding, InstallOperation, RuntimeTarget
from adv7sec_1_0.resources import missing_packaged_resources

_ARCH_TARGET = RuntimeTarget(
    distro_id="arch",
    distro_name="Arch Linux",
    package_manager="pacman",
    init_system="systemd",
    support_tier="native",
    kernel_release="audit-probe",
)
_CORE_FEATURES: tuple[str, ...] = ("auditd", "suricata", "unbound", "aide", "clamav", "lynis")


def _package_coverage_findings() -> list[Finding]:
    findings: list[Finding] = []
    missing: list[str] = []
    for feature in _CORE_FEATURES:
        report = build_install_report(
            _ARCH_TARGET,
            feature,
            Path("/tmp/adv7sec-audit"),
            False,
            False,
        )
        package_ops = [operation for operation in report.operations if operation.kind == "package"]
        if not package_ops or not package_ops[0].command:
            missing.append(feature)
    if missing:
        findings.append(
            Finding(
                id="AUDIT-006",
                severity="high",
                title="Feature selecionada nao agenda instalacao de pacote no backend nativo",
                evidence="Features sem operacao de pacote no plano Arch: " + ", ".join(missing),
                recommendation=(
                    "Derivar planner e backend do mesmo catalogo e garantir "
                    "pacote para cada core feature."
                ),
            )
        )
    return findings


def _noninteractive_findings() -> list[Finding]:
    findings: list[Finding] = []
    backend = build_backend_plan(_ARCH_TARGET)
    interactive = [
        action.feature
        for action in backend.package_actions
        if action.packages and "--noconfirm" not in action.command
    ]
    if interactive:
        findings.append(
            Finding(
                id="AUDIT-007",
                severity="high",
                title="Backend Arch ainda expoe caminho de apply interativo",
                evidence="Features sem --noconfirm no comando pacman: " + ", ".join(interactive),
                recommendation=(
                    "Tornar o apply do pacman explicitamente nao interativo "
                    "antes do host-real."
                ),
            )
        )
    with patch("adv7sec_1_0.install.os.geteuid", return_value=0):
        try:
            report = build_install_report(_ARCH_TARGET, "unbound", Path("/"), True, False)
            apply_install_report(report)
        except RuntimeError as error:
            if "--yes" in str(error):
                return findings
        findings.append(
            Finding(
                id="AUDIT-008",
                severity="high",
                title="Apply host-real nao exige confirmacao explicita",
                evidence="apply_install_report aceita host-real sem rejeitar a ausencia de --yes.",
                recommendation=(
                    "Bloquear install --apply --root / sem uma flag "
                    "de confirmacao explicita."
                ),
            )
        )
    return findings


def _blocking_validation_findings() -> list[Finding]:
    findings: list[Finding] = []
    operations = [
        InstallOperation(
            kind="validate",
            feature="unbound",
            summary="Validate unbound runtime",
            command=["unbound-checkconf"],
        ),
        InstallOperation(
            kind="service",
            feature="unbound",
            summary="Enable service unbound.service",
            command=["systemctl", "enable", "--now", "unbound.service"],
        ),
    ]

    def fake_runner(command: list[str], environment: dict[str, str]) -> int:
        del environment
        return 1 if command == ["unbound-checkconf"] else 0

    results = execute_operation_plan(operations, present=lambda _command: True, runner=fake_runner)
    service_results = [result for result in results if result.command[-1:] == ["unbound.service"]]
    if not service_results or service_results[0].status != "skipped":
        findings.append(
            Finding(
                id="AUDIT-009",
                severity="high",
                title="Falha de validacao nao bloqueia activacao de servico",
                evidence=(
                    "Sequencia simulada de validate->service nao marcou "
                    "o service como skipped."
                ),
                recommendation=(
                    "Parar o apply da feature quando a validacao "
                    "retornar codigo nao zero."
                ),
            )
        )
    return findings


def audit_repository(root: Path) -> list[Finding]:
    """Return high-signal audit findings for the current IPS_IDS repository."""

    findings: list[Finding] = []
    missing_resources = missing_packaged_resources()
    if missing_resources:
        findings.append(
            Finding(
                id="AUDIT-001",
                severity="critical",
                title="Core 1.0 ainda nao empacotou todos os recursos de runtime",
                evidence=(
                    "Recursos ausentes no pacote unificado: "
                    + ", ".join(missing_resources[:4])
                    + (" ..." if len(missing_resources) > 4 else "")
                ),
                recommendation="Completar o empacotamento de configs e helpers no core ativo.",
            )
        )
    readme = (root / "README.md").read_text(encoding="utf-8")
    response_doc = (root / "docs/RESPONSE.md").read_text(encoding="utf-8")
    ci_script = (root / "tests/ci-syntax-check.sh").read_text(encoding="utf-8")
    if "Linux-first" not in readme or "backend" not in readme:
        findings.append(
            Finding(
                id="AUDIT-002",
                severity="high",
                title="Escopo documentado nao promove claramente o core Linux-first",
                evidence="README.md nao descreve o backend cross-distro como interface primaria.",
                recommendation="Manter README alinhado ao runtime atual e ao catalogo unificado.",
            )
        )
    if "safe automatic response" not in response_doc:
        findings.append(
            Finding(
                id="AUDIT-003",
                severity="high",
                title="Resposta em tempo real nao esta documentada no contrato atual",
                evidence=(
                    "docs/RESPONSE.md nao descreve resposta automatica "
                    "segura como capability ativa."
                ),
                recommendation=(
                    "Documentar resposta segura com gates explicitos "
                    "e modo preview-first."
                ),
            )
        )
    if "ruff" not in ci_script or "mypy" not in ci_script:
        findings.append(
            Finding(
                id="AUDIT-004",
                severity="medium",
                title="Gate Python atual nao cobre lint nem type-check estrito",
                evidence="tests/ci-syntax-check.sh ainda nao executa ambos ruff e mypy --strict.",
                recommendation="Manter lint e type-check estrito no gate do projeto ativo.",
            )
        )
    if not (root / "tests/test_adv7sec_cli.py").is_file() or not (
        root / "tests/test_adv7sec_install.py"
    ).is_file():
        findings.append(
            Finding(
                id="AUDIT-005",
                severity="medium",
                title="Testes dedicados de CLI e install/apply estao ausentes",
                evidence="A raiz ativa precisa manter suites dedicadas sob tests/.",
                recommendation=(
                    "Preservar cobertura da CLI principal e do "
                    "install/apply no runtime ativo."
                ),
            )
        )
    findings.extend(_package_coverage_findings())
    findings.extend(_noninteractive_findings())
    findings.extend(_blocking_validation_findings())
    return findings
