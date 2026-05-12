"""kiterunner scan stage — API route discovery alongside ffuf.

[v0.5.0] Vault citation: hacking-apis p. 124 (`assetnote/kiterunner`).

Command shape derived from observed `kiterunner scan -h` against
kiterunner v1.0.2 (binary name: `kiterunner`, despite docs occasionally
calling it `kr`):

    kiterunner -o json scan <url> -w <wordlist> -H "<header>" --quiet

`-o json` is a global flag — it must precede the `scan` subcommand. The
binary streams JSON-formatted findings to stdout; the runner already
captures stdout to `runs/<UTC>/logs/<label>.stdout.log`, so parse_results
reads that log file (path threaded via `CommandPlan.artifacts`).
"""

import json
from pathlib import Path

from bbwebscan.auth import build_header_args
from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig

# kiterunner status code → severity. 200/3xx = info (route exists, public);
# 401/403 = low (route exists but auth-rejected; signals scope info that may
# be useful for further work).
_LOW_STATUSES: frozenset[int] = frozenset({401, 403})
_INFO_MIN: int = 200
_INFO_MAX: int = 399


def build_plans(
    config: RunConfig, artifacts: RunArtifacts, urls: list[str]
) -> list[CommandPlan]:
    plans: list[CommandPlan] = []
    common_headers = build_header_args(config.auth)
    for index, url in enumerate(urls, start=1):
        label = f"kiterunner_{index}"
        # parse_results reads the runner's stdout_log for this label.
        # Path mirrors runner.run_plan's `artifacts.logs / f"{label}.stdout.log"`.
        stdout_log = artifacts.root / "logs" / f"{label}.stdout.log"
        command: list[str] = [
            "kiterunner",
            "-o", "json",
            "-q",
            "scan", url,
            "-w", str(config.wordlist),
            *common_headers,
        ]
        plans.append(
            CommandPlan(
                stage="discovery",
                label=label,
                command=command,
                artifacts=[stdout_log],
            )
        )
    return plans


def parse_results(artifact_paths: list[Path]) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    routes: list[str] = []
    for path in artifact_paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            url = payload.get("uri") or payload.get("url") or payload.get("target")
            status = payload.get("status_code")
            if not isinstance(url, str):
                continue
            if not isinstance(status, int):
                continue
            severity = _classify(status)
            if severity is None:
                continue
            routes.append(url)
            findings.append(
                Finding(
                    stage="discovery",
                    kind="api-route",
                    target=url,
                    severity=severity,
                    title=f"kiterunner found API route status={status}",
                    evidence=str(path),
                )
            )
    return findings, list(dict.fromkeys(routes))


def _classify(status: int) -> str | None:
    if status in _LOW_STATUSES:
        return "low"
    if _INFO_MIN <= status <= _INFO_MAX:
        return "info"
    return None
