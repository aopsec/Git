from pathlib import Path

from bbwebscan.auth import build_header_args
from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig
from bbwebscan.stages._jsonl import load_json_or_jsonl

DISCOVERY_TOOLS: tuple[str, ...] = ("ffuf", "feroxbuster", "dirsearch")


def build_plans(config: RunConfig, artifacts: RunArtifacts, urls: list[str]) -> list[CommandPlan]:
    plans: list[CommandPlan] = []
    for tool_name in (tool for tool in DISCOVERY_TOOLS if tool in config.enabled_tools):
        for index, url in enumerate(urls, start=1):
            label = f"{tool_name}_{index}"
            output_file = artifacts.artifacts / f"{label}.json"
            plans.append(
                CommandPlan(
                    stage="discovery",
                    label=label,
                    command=_tool_command(tool_name, config, url, output_file),
                    artifacts=[output_file],
                )
            )
    return plans


def _tool_command(tool_name: str, config: RunConfig, url: str, output_file: Path) -> list[str]:
    common_headers = build_header_args(config.auth)
    if tool_name == "ffuf":
        command = [
            "ffuf",
            "-u", f"{url.rstrip('/')}/FUZZ",
            "-w", str(config.wordlist),
            "-ac",
            "-of", "json",
            "-o", str(output_file),
            "-t", str(config.threads),
            "-rate", str(config.rate),
            *common_headers,
        ]
        if config.auth.raw_request is not None:
            command.extend(["-request", str(config.auth.raw_request)])
        return command
    if tool_name == "feroxbuster":
        return [
            "feroxbuster",
            "-u", url,
            "-w", str(config.wordlist),
            "--json",
            "-o", str(output_file),
            "-t", str(config.threads),
            *common_headers,
        ]
    # dirsearch
    command = [
        "dirsearch",
        "-u", url,
        "-w", str(config.wordlist),
        # [FIX-BBW-03] dirsearch v0.4.3 exposes report output as -O/-o.
        "-O", "json",
        "-o", str(output_file),
        *common_headers,
    ]
    if config.auth.raw_request is not None:
        command.append(f"--raw={config.auth.raw_request}")
    return command


def parse_results(
    artifact_paths: list[Path],
    config: RunConfig | None = None,
) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    aggregated_urls: list[str] = []
    status_filter = (config.discovery_status_filter if config else None) or []
    for artifact_path in artifact_paths:
        artifact_urls = _extract_urls_from_artifact(artifact_path, status_filter)
        aggregated_urls.extend(artifact_urls)
        if artifact_urls:
            findings.append(
                Finding(
                    stage="discovery",
                    kind="content",
                    target=artifact_urls[0],
                    severity="info",
                    title=f"Discovered {len(artifact_urls)} web content candidates",
                    evidence=str(artifact_path),
                )
            )
    return findings, list(dict.fromkeys(aggregated_urls))


def _extract_urls_from_artifact(
    artifact_path: Path,
    status_filter: list[str] | None = None,
) -> list[str]:
    urls: list[str] = []
    status_filter_set = set(status_filter) if status_filter else set()
    for payload in load_json_or_jsonl(artifact_path):
        urls.extend(_extract_urls(payload, status_filter_set))
    return urls


def _extract_urls(payload: dict[str, object], status_filter: set[str] | None = None) -> list[str]:
    results = payload.get("results")
    if isinstance(results, list):
        extracted = []
        for item in results:
            if isinstance(item, dict) and isinstance(item.get("url"), str):
                # If status_filter is provided and non-empty, only include URLs with matching status
                if status_filter:
                    status = str(item.get("status", ""))
                    if status not in status_filter:
                        continue
                extracted.append(item["url"])
        return extracted
    candidate = payload.get("url")
    if isinstance(candidate, str):
        # Single URL case (e.g., top-level response); check status if filter provided
        if status_filter:
            status = str(payload.get("status", ""))
            if status not in status_filter:
                return []
        return [candidate]
    return []
