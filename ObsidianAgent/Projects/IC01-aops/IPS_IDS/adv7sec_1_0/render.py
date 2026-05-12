"""CLI render helpers."""

from __future__ import annotations

import json

from adv7sec_1_0.models import (
    AnalysisReport,
    BackendPlan,
    BuildPlan,
    Finding,
    InstallReport,
    OutputMode,
    ResourceRecord,
    ResponsePlan,
)


def emit_findings(findings: list[Finding], mode: OutputMode) -> int:
    if mode == "json":
        print(json.dumps([finding.model_dump(mode="json") for finding in findings], indent=2))
        return 0
    for finding in findings:
        print(f"[{finding.severity.upper()}] {finding.id} {finding.title}")
        print(f"  evidence: {finding.evidence}")
        print(f"  recommendation: {finding.recommendation}")
    return 0


def emit_plan(plan: BuildPlan, mode: OutputMode) -> int:
    if mode == "json":
        print(plan.model_dump_json(indent=2))
        return 0
    print(f"ADV7Sec {plan.version} for {plan.target.distro_name} ({plan.target.support_tier})")
    print("Goals:")
    for goal in plan.goals:
        print(f"- {goal}")
    print("Runtime layout:")
    for item in plan.runtime_layout:
        print(f"- {item}")
    print("Cleanup after parity:")
    for item in plan.cleanup_after_parity:
        print(f"- {item}")
    print("Steps:")
    for step in plan.steps:
        print(f"- {step.id}: {step.title} -> {step.objective}")
    return 0


def emit_backend(plan: BackendPlan, mode: OutputMode) -> int:
    if mode == "json":
        print(plan.model_dump_json(indent=2))
        return 0
    print(f"package_manager={plan.package_manager} service_manager={plan.service_manager}")
    for action in plan.package_actions:
        print(f"- pkg:{action.feature} status={action.status}")
    for binding in plan.service_bindings:
        print(f"- svc:{binding.feature} unit={binding.unit}")
    return 0


def emit_response(plan: ResponsePlan, mode: OutputMode) -> int:
    if mode == "json":
        print(plan.model_dump_json(indent=2))
        return 0
    print(f"action={plan.action} execute={int(plan.execute)}")
    print("command=" + " ".join(plan.command))
    return 0


def emit_analysis(report: AnalysisReport, mode: OutputMode) -> int:
    if mode == "json":
        print(report.model_dump_json(indent=2))
        return 0
    print(f"events={report.total_events} elevated={report.elevated_events}")
    for signal in report.signals:
        print(f"- {signal}")
    for event in report.events[:5]:
        print(f"[{event.severity}] {event.source} :: {event.summary}")
    for decision in report.responses:
        print(
            f"response={decision.action} target={decision.target} "
            f"confidence={decision.confidence}"
        )
    return 0


def emit_install(report: InstallReport, mode: OutputMode) -> int:
    if mode == "json":
        print(report.model_dump_json(indent=2))
        return report.exit_code
    print(
        f"root={report.root_dir} execute={int(report.execute)} "
        f"confirm={int(report.confirm)} exit_code={report.exit_code}"
    )
    print("features=" + ",".join(report.features))
    for operation in report.operations:
        if operation.command:
            env_prefix = ""
            if operation.environment:
                env_prefix = " ".join(
                    f"{key}={value}" for key, value in sorted(operation.environment.items())
                ) + " "
            command_text = " ".join(operation.command)
            print(f"- {operation.kind}:{operation.feature} {env_prefix}{command_text}")
        elif operation.path is not None:
            print(f"- {operation.kind}:{operation.feature} {operation.path}")
        else:
            print(f"- {operation.kind}:{operation.feature} {operation.summary}")
    for result in report.results:
        print(
            f"= {result.status}:{result.kind}:{result.feature} "
            f"rc={result.returncode if result.returncode is not None else 'na'} {result.detail}"
        )
    for warning in report.warnings:
        print(f"! {warning}")
    return report.exit_code


def emit_resources(records: list[ResourceRecord], mode: OutputMode, export_dir: str | None) -> int:
    if mode == "json":
        print(json.dumps([record.model_dump(mode="json") for record in records], indent=2))
        return 0
    for record in records:
        print(f"[{int(record.packaged)}] {record.path}")
    if export_dir is not None:
        print(f"exported_to={export_dir}")
    return 0
