import sys
from pathlib import Path

from bbwebscan.auth import build_header_args
from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig
from bbwebscan.runner import write_lines
from bbwebscan.stages._jsonl import iter_jsonl


def build_plan(config: RunConfig, artifacts: RunArtifacts, urls: list[str]) -> list[CommandPlan]:
    input_file = artifacts.artifacts / "nuclei_targets.txt"
    output_file = artifacts.artifacts / "nuclei.jsonl"

    # [SEC-BBW-03] Apply target cap to prevent target explosion and timeouts.
    capped_urls = urls[:config.nuclei_max_targets]
    if len(urls) > config.nuclei_max_targets:
        print(
            f"[bbwebscan] warning: nuclei target count ({len(urls)}) exceeds max_targets "
            f"({config.nuclei_max_targets}); truncating to first {config.nuclei_max_targets}",
            file=sys.stderr,
        )

    write_lines(input_file, capped_urls)
    command = [
        "nuclei",
        "-l", str(input_file),
        "-jsonl",
        "-o", str(output_file),
        "-rl", str(config.rate),
        "-c", str(config.threads),
        "-timeout", str(config.tool_timeout_s),
        *build_header_args(config.auth),
    ]
    return [
        CommandPlan(stage="nuclei", label="nuclei", command=command, artifacts=[output_file])
    ]


def parse_results(output_file: Path) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    for payload in iter_jsonl(output_file):
        raw_info = payload.get("info")
        info: dict[str, object] = raw_info if isinstance(raw_info, dict) else {}
        severity = str(info.get("severity", "info"))
        title = str(info.get("name", "Nuclei finding"))
        target = str(payload.get("matched-at", "unknown"))
        findings.append(
            Finding(
                stage="nuclei",
                kind="template-match",
                target=target,
                severity=severity,
                title=title,
                evidence=str(output_file),
            )
        )
    return findings, []
