import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from bbwebscan.auth import build_header_args
from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig
from bbwebscan.runner import write_lines
from bbwebscan.stages._jsonl import iter_jsonl


def _strip_fragment(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))


def build_plan(config: RunConfig, artifacts: RunArtifacts, urls: list[str]) -> list[CommandPlan]:
    input_file = artifacts.artifacts / "nuclei_targets.txt"
    output_file = artifacts.artifacts / "nuclei.jsonl"

    # Strip URL fragments (#...) — HTTP does not transmit them, so they only
    # create duplicate requests against the same server path.
    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        clean = _strip_fragment(url)
        if clean not in seen:
            seen.add(clean)
            deduped.append(clean)

    # [SEC-BBW-03] Apply target cap to prevent target explosion and timeouts.
    capped_urls = deduped[:config.nuclei_max_targets]
    if len(deduped) > config.nuclei_max_targets:
        print(
            f"[bbwebscan] warning: nuclei target count ({len(deduped)}) exceeds max_targets "
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
        "-tags", "cve,misconfig,exposure,tech",
        "-etags", "dos,bruteforce,fuzz,intrusive",
        "-duc",  # skip update check on each run
        "-ni",   # disable interactsh to avoid OOB wait adding to wall clock
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
