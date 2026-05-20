from pathlib import Path

from bbwebscan.auth import build_header_args
from bbwebscan.models import CommandPlan, Finding, NormalizedTarget, RunArtifacts, RunConfig
from bbwebscan.runner import write_lines
from bbwebscan.stages._jsonl import iter_jsonl


def build_plan(
    config: RunConfig, artifacts: RunArtifacts, targets: list[NormalizedTarget]
) -> list[CommandPlan]:
    input_file = artifacts.artifacts / "httpx_targets.txt"
    output_file = artifacts.artifacts / "httpx.jsonl"
    write_lines(input_file, [target.seed_url for target in targets])
    command = [
        "httpx",
        "-silent",
        "-json",
        "-l", str(input_file),
        "-o", str(output_file),
        "-status-code",
        "-title",
        "-tech-detect",
        "-web-server",
        "-ip",
        "-cname",
        "-threads", str(config.threads),
        "-rl", str(config.rate),
        "-timeout", str(config.tool_timeout_s),
        *build_header_args(config.auth),
    ]
    return [
        CommandPlan(stage="httpx", label="httpx", command=command, artifacts=[output_file])
    ]


def parse_results(output_file: Path) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    urls: list[str] = []
    for payload in iter_jsonl(output_file):
        url = payload.get("url")
        if not isinstance(url, str):
            continue
        urls.append(url)
        status_code = payload.get("status_code", "unknown")
        findings.append(
            Finding(
                stage="httpx",
                kind="inventory",
                target=url,
                severity="info",
                title=f"Live web target status={status_code}",
                evidence=str(output_file),
            )
        )
    return findings, list(dict.fromkeys(urls))
