"""Scrapy crawler stage.

Drives ``bbwebscan/stages/scrapy/bbspider.py`` via ``scrapy runspider`` and
parses the resulting JSONL into bbWebScan findings. Mirrors the shape of
``katana_stage`` so the pipeline can treat scrapy as a peer crawler.

Severity policy:
    info   — crawl summary, plain emails, info_disclosure
    low    — exposed documents (PDF/DOCX/backup archives)
    medium — exposed admin paths (.git, .env, wp-admin, backups)
    high   — secret-pattern hits (only when --scrapy-deep). Evidence is the
             SHA-256 prefix from the spider; raw secret values are never
             persisted.

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
    targets_file = artifacts.artifacts / "scrapy_targets.txt"
    output_file = artifacts.artifacts / "scrapy.jsonl"
    log_file = artifacts.logs / "scrapy.log"
    write_lines(targets_file, urls)
    spider_path = Path(__file__).resolve().parent / "scrapy" / "bbspider.py"
    # [FIX-V2] Use venv-relative scrapy binary to avoid system Twisted 26.4.0
    # incompatibility (_setAcceptableProtocols removal breaks system scrapy).
    scrapy_bin = str(Path(sys.executable).parent / "scrapy")
    command = [
        scrapy_bin,
        "runspider",
        str(spider_path),
        "-O", str(output_file),
        "-a", f"urls_file={targets_file}",
        "-a", f"max_depth={config.scrapy_max_depth}",
        "-a", f"deep_mode={int(config.scrapy_deep)}",
        "-a", f"js_render={int(config.scrapy_js_render)}",
        "-s", f"LOG_FILE={log_file}",
        "-s", f"CLOSESPIDER_TIMEOUT={config.command_wall_clock_s}",
    ]
    return [
        CommandPlan(stage="scrapy", label="scrapy", command=command, artifacts=[output_file])
    ]


def parse_results(  # noqa: PLR0912 - fan-out over scrapy item fields is naturally wide
    output_file: Path,
) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    crawled_urls: list[str] = []
    document_targets: set[str] = set()
    exposed_targets: set[str] = set()
    email_pages: set[str] = set()
    secret_records: list[tuple[str, str, str, str]] = []

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
        secrets = payload.get("secrets")
        if isinstance(secrets, list):
            for entry in secrets:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                digest = entry.get("evidence_sha256")
                confidence = entry.get("confidence", "medium")
                source = entry.get("source_url") or (url if isinstance(url, str) else "")
                if (
                    isinstance(name, str)
                    and isinstance(digest, str)
                    and isinstance(confidence, str)
                    and isinstance(source, str)
                ):
                    secret_records.append((name, digest, confidence, source))

    deduped_urls = list(dict.fromkeys(crawled_urls))

    if deduped_urls:
        findings.append(
            Finding(
                stage="scrapy",
                kind="crawl",
                target=deduped_urls[0],
                severity="info",
                title=f"Scrapy crawled {len(deduped_urls)} URLs",
                evidence=str(output_file),
            )
        )

    if email_pages:
        findings.append(
            Finding(
                stage="scrapy",
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
                stage="scrapy",
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
                stage="scrapy",
                kind="exposed-path",
                target=path,
                severity="medium",
                title="Sensitive path reference (admin/backup/dotfile)",
                evidence=str(output_file),
            )
        )

    seen_secret_keys: set[tuple[str, str]] = set()
    for name, digest, confidence, source in secret_records:
        key = (name, digest)
        if key in seen_secret_keys:
            continue
        seen_secret_keys.add(key)
        severity = _CONFIDENCE_TO_SEVERITY.get(confidence, "medium")
        findings.append(
            Finding(
                stage="scrapy",
                kind="exposed-secret",
                target=source,
                severity=severity,
                title=f"{name} pattern matched",
                evidence=f"sha256:{digest} @ {source}",
            )
        )

    return findings, deduped_urls


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
