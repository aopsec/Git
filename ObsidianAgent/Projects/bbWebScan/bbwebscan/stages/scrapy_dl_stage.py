"""Scrapy extended downloader stage — complementary harvesting of exposed assets.

Drives ``bbwebscan/stages/scrapy/url_downloader.py`` via ``scrapy runspider`` and
parses the resulting JSONL into bbWebScan findings. Mirrors the shape of
``scrapy_stage`` to integrate seamlessly into the pipeline.

Extracts:
- Email addresses
- Exposed paths (.git, .env, admin paths, etc.)
- Linked documents (PDF, DOCX, SQL dumps, archives)

Severity policy (same as scrapy_stage):
    info   — crawl summary, emails found, info_disclosure
    low    — exposed documents
    medium — exposed admin/backup paths
    high   — reserved for secret patterns (if deep_mode enabled in future)

cyberref: PENDING attestation.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig
from bbwebscan.runner import write_lines
from bbwebscan.stages._jsonl import iter_jsonl

_CONFIDENCE_TO_SEVERITY: dict[str, str] = {
    "high": "high",
    "medium": "medium",
    "low": "low",
}


def build_plan(config: RunConfig, artifacts: RunArtifacts, urls: list[str]) -> list[CommandPlan]:
    targets_file = artifacts.artifacts / "scrapy_extended_targets.txt"
    output_file = artifacts.artifacts / "scrapy_extended.jsonl"
    log_file = artifacts.logs / "scrapy_extended.log"
    write_lines(targets_file, urls)
    spider_path = Path(__file__).resolve().parent / "scrapy" / "url_downloader.py"
    # Use venv-relative scrapy binary to avoid system Twisted incompatibility.
    scrapy_bin = str(Path(sys.executable).parent / "scrapy")
    command = [
        scrapy_bin,
        "runspider",
        str(spider_path),
        "-O", str(output_file),
        "-a", f"urls_file={targets_file}",
        "-a", f"max_depth={config.scrapy_max_depth}",
        "-a", f"js_render={int(config.scrapy_js_render)}",
        "-s", f"LOG_FILE={log_file}",
        "-s", f"CLOSESPIDER_TIMEOUT={config.command_wall_clock_s}",
    ]
    return [
        CommandPlan(stage="scrapy-dl", label="scrapy-dl", command=command, artifacts=[output_file])
    ]


def parse_results(
    output_file: Path,
) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    crawled_urls: list[str] = []
    document_targets: set[str] = set()
    exposed_targets: set[str] = set()
    email_pages: set[str] = set()

    for payload in iter_jsonl(output_file):
        url = payload.get("url")
        if isinstance(url, str):
            crawled_urls.append(url)
        if isinstance(payload.get("links"), list):
            for link in payload["links"]:
                if isinstance(link, str):
                    crawled_urls.append(link)
        for doc in _as_str_list(payload.get("documents")):
            document_targets.add(doc)
        for path in _as_str_list(payload.get("exposed_paths")):
            exposed_targets.add(path)
        emails = _as_str_list(payload.get("emails"))
        if emails and isinstance(url, str):
            email_pages.add(url)

    deduped_urls = list(dict.fromkeys(crawled_urls))

    if deduped_urls:
        findings.append(
            Finding(
                stage="scrapy-dl",
                kind="crawl",
                target=deduped_urls[0],
                severity="info",
                title=f"Scrapy-extended crawled {len(deduped_urls)} URLs",
                evidence=str(output_file),
            )
        )

    if email_pages:
        findings.append(
            Finding(
                stage="scrapy-dl",
                kind="info-disclosure-email",
                target=next(iter(sorted(email_pages))),
                severity="info",
                title=f"Emails found on {len(email_pages)} page(s)",
                evidence=str(output_file),
            )
        )

    for doc in sorted(document_targets):
        findings.append(
            Finding(
                stage="scrapy-dl",
                kind="exposed-document",
                target=doc,
                severity="low",
                title="Document file linked from in-scope page",
                evidence=str(output_file),
            )
        )

    for path in sorted(exposed_targets):
        findings.append(
            Finding(
                stage="scrapy-dl",
                kind="exposed-path",
                target=path,
                severity="medium",
                title="Sensitive path reference (admin/backup/dotfile)",
                evidence=str(output_file),
            )
        )

    return findings, deduped_urls


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
