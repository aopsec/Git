"""naabu port-discovery stage — open ports for each in-scope target.

[v0.5.6] Vault citation: hacking-apis (ProjectDiscovery appendix).

Position: amass → naabu → httpx → ... naabu discovers open ports per FQDN so
httpx (and every downstream stage) probes the actual listening sockets rather
than the implicit ``:80``/``:443`` pair derived from a URL scheme.

Command shape derived from observed ``naabu -h`` against v2.6.x:

    naabu -host <fqdn> -top-ports 100 -rate 1000 -timeout 1000 \\
          -json -o <prefix>.jsonl -silent

- ``-top-ports {100,1000}`` for the corresponding modes; ``-p -`` (full sweep)
  is gated by ``--ack-authorized`` in ``config.build_run_config`` because a
  65k-port sweep is a detectable scan profile.
- ``-silent`` keeps stdout clean (matches the httpx/nuclei convention).
- ``-json -o <file>.jsonl`` emits JSONL we parse via ``iter_jsonl``.
- naabu defaults to TCP-CONNECT; we do NOT inject ``-scan-type s`` (SYN, root)
  silently. Operators wanting SYN must supply it via a future profile knob.

Output is a list of ``host:port`` strings the pipeline appends to its open-port
set; ``_run_httpx`` consumes them to derive seed URLs in addition to the plain
host targets.
"""

from pathlib import Path

from bbwebscan.models import CommandPlan, Finding, NormalizedTarget, RunArtifacts, RunConfig
from bbwebscan.stages._jsonl import iter_jsonl

_TOP_PORTS: dict[str, str] = {
    "top-100": "100",
    "top-1000": "1000",
}
_DEFAULT_TIMEOUT_MS: int = 1000


def build_plan(
    config: RunConfig, artifacts: RunArtifacts, targets: list[NormalizedTarget]
) -> list[CommandPlan]:
    if not targets:
        return []
    hosts = sorted({target.host for target in targets})
    output_file = artifacts.artifacts / "naabu.jsonl"
    command: list[str] = [
        "naabu",
        "-host", ",".join(hosts),
        "-rate", str(config.port_scan_rate),
        "-timeout", str(_DEFAULT_TIMEOUT_MS),
        "-json",
        "-o", str(output_file),
        "-silent",
    ]
    if config.port_scan_mode == "full":
        command.extend(["-p", "-"])
    else:
        command.extend(["-top-ports", _TOP_PORTS[config.port_scan_mode]])
    return [
        CommandPlan(stage="naabu", label="naabu", command=command, artifacts=[output_file])
    ]


def parse_results(output_file: Path) -> tuple[list[Finding], list[str]]:
    """Read naabu JSONL and emit (one summary finding, list of host:port)."""
    findings: list[Finding] = []
    host_ports: list[str] = []
    for payload in iter_jsonl(output_file):
        host = payload.get("host")
        port = payload.get("port")
        if not isinstance(host, str) or not isinstance(port, int):
            continue
        host_ports.append(f"{host}:{port}")
    deduped = list(dict.fromkeys(host_ports))
    if deduped:
        findings.append(
            Finding(
                stage="naabu",
                kind="open-port",
                target=deduped[0].split(":", 1)[0],
                severity="info",
                title=f"Discovered {len(deduped)} open ports via naabu",
                evidence=str(output_file),
            )
        )
    return findings, deduped
