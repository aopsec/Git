"""Unified CLI for ADV7Sec 1.0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from adv7sec_1_0.analysis import analyze_events
from adv7sec_1_0.audit import audit_repository
from adv7sec_1_0.backends import build_backend_plan
from adv7sec_1_0.events import collect_live_events
from adv7sec_1_0.feature_catalog import feature_choices
from adv7sec_1_0.install import apply_install_report, build_install_report
from adv7sec_1_0.linux import detect_runtime_target, probe_capabilities
from adv7sec_1_0.models import ActionName, OutputMode, ResourceRecord
from adv7sec_1_0.monitor import snapshot_monitor
from adv7sec_1_0.plan import build_plan
from adv7sec_1_0.render import (
    emit_analysis,
    emit_backend,
    emit_findings,
    emit_install,
    emit_plan,
    emit_resources,
    emit_response,
)
from adv7sec_1_0.resources import (
    export_packaged_resources,
    list_packaged_resources,
    missing_packaged_resources,
)
from adv7sec_1_0.response import build_response_from_decision, build_response_plan
from adv7sec_1_0.smoke import run_smoke_checks


def _add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json"), default="text")


def build_parser() -> argparse.ArgumentParser:
    """Create the ADV7Sec 1.0 CLI."""
    parser = argparse.ArgumentParser(description="ADV7Sec 1.0 unified Linux-first control plane")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("audit", "Deep audit of the current IPS_IDS repository"),
        ("doctor", "Detect distro, init system, and runtime capabilities"),
        ("backend", "Show package and service adapters for the detected distro"),
        ("plan", "Build the staged plan for the unified 1.0 version"),
        ("install", "Plan or apply the unified resource-backed install"),
        ("monitor", "Snapshot recent live logs"),
        ("analyze", "Analyze live telemetry and derive safe auto-response"),
        ("smoke", "Run basic smoke checks against one root directory"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        _add_format_argument(command)
        if name in {"monitor", "analyze"}:
            command.add_argument("--lines", type=int, default=20)
        if name == "analyze":
            command.add_argument("--execute", action="store_true")
        if name == "install":
            command.add_argument(
                "--feature",
                choices=("all", *feature_choices()),
                default="all",
            )
            command.add_argument("--root", default="/")
            command.add_argument("--apply", action="store_true")
            command.add_argument("--yes", action="store_true")
        if name == "smoke":
            command.add_argument("--root", default="/")
    resources = subparsers.add_parser("resources", help="List, verify, or export resources")
    _add_format_argument(resources)
    resources.add_argument("--export-dir")
    respond = subparsers.add_parser("respond", help="Preview or execute a safe response action")
    _add_format_argument(respond)
    respond.add_argument(
        "action",
        choices=("stop-service", "disable-service", "kill-pid", "quarantine-path"),
    )
    respond.add_argument("target")
    respond.add_argument("--execute", action="store_true")
    return parser


def _doctor_payload(mode: OutputMode) -> int:
    target = detect_runtime_target()
    capabilities = probe_capabilities()
    backend = build_backend_plan(target)
    if mode == "json":
        print(
            json.dumps(
                {
                    "target": target.model_dump(mode="json"),
                    "capabilities": [item.model_dump(mode="json") for item in capabilities],
                    "backend": backend.model_dump(mode="json"),
                },
                indent=2,
            )
        )
        return 0
    print(
        "target="
        f"{target.distro_name} pkg={target.package_manager} "
        f"init={target.init_system} support={target.support_tier}"
    )
    for capability in capabilities:
        print(f"- cap:{capability.name} available={int(capability.available)} {capability.detail}")
    return emit_backend(backend, "text")


def _resource_records(export_dir: str | None) -> list[ResourceRecord]:
    packaged = set(list_packaged_resources())
    records = [
        ResourceRecord(path=resource_path, packaged=resource_path in packaged)
        for resource_path in sorted(packaged | set(missing_packaged_resources()))
    ]
    if export_dir is not None:
        export_packaged_resources(Path(export_dir))
    return records


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    mode: OutputMode = args.format
    root = Path(__file__).resolve().parents[1]
    try:
        if args.command == "audit":
            return emit_findings(audit_repository(root), mode)
        if args.command == "doctor":
            return _doctor_payload(mode)
        if args.command == "backend":
            return emit_backend(build_backend_plan(detect_runtime_target()), mode)
        if args.command == "plan":
            target = detect_runtime_target()
            return emit_plan(build_plan(target, audit_repository(root)), mode)
        if args.command == "install":
            install_report = build_install_report(
                detect_runtime_target(),
                args.feature,
                Path(args.root),
                args.apply,
                args.yes,
            )
            if args.apply:
                install_report = apply_install_report(install_report)
            return emit_install(install_report, mode)
        if args.command == "monitor":
            records = snapshot_monitor(args.lines)
            if mode == "json":
                print(json.dumps([record.model_dump(mode="json") for record in records], indent=2))
                return 0
            for record in records:
                print(f"[{record.status}] {record.source}")
                print(record.summary)
                print("---")
            return 0
        if args.command == "analyze":
            analysis_report = analyze_events(collect_live_events(args.lines), args.execute)
            for decision in analysis_report.responses if args.execute else []:
                build_response_from_decision(decision)
            return emit_analysis(analysis_report, mode)
        if args.command == "resources":
            return emit_resources(_resource_records(args.export_dir), mode, args.export_dir)
        if args.command == "smoke":
            records = run_smoke_checks(Path(args.root))
            if mode == "json":
                print(json.dumps([record.model_dump(mode="json") for record in records], indent=2))
                return 0
            for record in records:
                print(f"[{record.status}] {record.source}")
                print(record.summary)
            return 0
        action: ActionName = args.action
        return emit_response(build_response_plan(action, args.target, args.execute), mode)
    except RuntimeError as error:
        print(f"error: {error}")
        return 1
