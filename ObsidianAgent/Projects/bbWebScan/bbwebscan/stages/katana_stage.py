from pathlib import Path

from bbwebscan.auth import build_header_args
from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig
from bbwebscan.runner import write_lines
from bbwebscan.stages._jsonl import iter_jsonl


def build_plan(config: RunConfig, artifacts: RunArtifacts, urls: list[str]) -> list[CommandPlan]:
    input_file = artifacts.artifacts / "katana_targets.txt"
    output_file = artifacts.artifacts / "katana.jsonl"
    write_lines(input_file, urls)
    command = [
        "katana",
        "-list", str(input_file),
        "-jsonl",
        "-silent",
        "-o", str(output_file),
        "-concurrency", str(config.threads),
        "-rate-limit", str(config.rate),
        *build_header_args(config.auth),
    ]
    return [
        CommandPlan(stage="katana", label="katana", command=command, artifacts=[output_file])
    ]


def parse_results(output_file: Path) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    urls: list[str] = []
    for payload in iter_jsonl(output_file):
        request = payload.get("request")
        url: object = None
        if isinstance(request, dict):
            url = request.get("endpoint")
        if not isinstance(url, str):
            url = payload.get("url")
        if isinstance(url, str):
            urls.append(url)
    if urls:
        findings.append(
            Finding(
                stage="katana",
                kind="crawl",
                target=urls[0],
                severity="info",
                title=f"Discovered {len(set(urls))} crawl URLs",
                evidence=str(output_file),
            )
        )
    return findings, list(dict.fromkeys(urls))
