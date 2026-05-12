from pathlib import Path

from bbwebscan.auth import build_header_lines
from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig
from bbwebscan.stages._jsonl import load_json_or_jsonl

ARJUN_MAX_TARGETS: int = 10


def build_plans(config: RunConfig, artifacts: RunArtifacts, urls: list[str]) -> list[CommandPlan]:
    plans: list[CommandPlan] = []
    for index, url in enumerate(urls[:ARJUN_MAX_TARGETS], start=1):
        output_file = artifacts.artifacts / f"arjun_{index}.json"
        header_lines = build_header_lines(config.auth)
        command = [
            "arjun",
            "-u", url,
            "-oJ", str(output_file),
            "-t", str(config.threads),
        ]
        if header_lines:
            # [FIX-BBW-04] Arjun accepts one --headers value with newline-separated headers.
            command.extend(["--headers", "\n".join(header_lines)])
        plans.append(
            CommandPlan(
                stage="params",
                label=f"arjun_{index}",
                command=command,
                artifacts=[output_file],
            )
        )
    return plans


def parse_results(artifact_paths: list[Path]) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    for artifact_path in artifact_paths:
        params = _flatten_params_for_artifact(artifact_path)
        if not params:
            continue
        sample = ", ".join(sorted(params)[:5])
        findings.append(
            Finding(
                stage="params",
                kind="parameter",
                target=str(artifact_path),
                severity="info",
                title=f"Discovered {len(params)} parameters: {sample}",
                evidence=str(artifact_path),
            )
        )
    return findings, []


def _flatten_params_for_artifact(artifact_path: Path) -> set[str]:
    params: set[str] = set()
    for payload in load_json_or_jsonl(artifact_path):
        for key, value in payload.items():
            if isinstance(value, list):
                params.update(str(item) for item in value if isinstance(item, str))
            elif isinstance(value, str):
                params.add(value)
            else:
                params.add(str(key))
    return params
