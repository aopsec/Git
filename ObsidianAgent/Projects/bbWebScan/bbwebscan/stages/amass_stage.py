"""amass enum stage — subdomain enumeration before httpx.

[v0.5.0] Vault citation: hacking-apis p. 123 (`OWASP/Amass`).

Command shape derived from observed `amass enum -h` against amass v4.2.0:

    amass enum -d <root> -oA <prefix> -timeout <minutes> [-active] -nocolor

`-oA <prefix>` writes `<prefix>.txt` (one FQDN per line) plus other artefacts.
We only consume `<prefix>.txt`. `-passive` is deprecated upstream (passive is
the default), so we never emit it. `-active` is gated by `--ack-authorized`
in `config.build_run_config`.

Rate-limit caveat: amass v4.2.0 deprecated `-max-dns-queries` in favour of
`-dns-qps`. `config.rate` does NOT directly throttle amass — operators who
need throttling must set `dns-qps` via a profile-supplied amass config in a
future release. We do not silently inject the flag here.
"""

from pathlib import Path

from bbwebscan.models import CommandPlan, Finding, NormalizedTarget, RunArtifacts, RunConfig
from bbwebscan.targets import canonical_host, is_public_suffix_only, registrable_domain

_DEFAULT_TIMEOUT_MINUTES: int = 10


def _root_domain(host: str) -> str:
    """Return the registrable root: 'sub.api.example.com' → 'example.com'.

    [SEC-BBW-02] Use PSL-backed eTLD+1 selection. If the computed root is an
    exact public/shared suffix, stay constrained to the exact target host.
    """
    lowered = canonical_host(host)
    root = registrable_domain(lowered)
    return lowered if is_public_suffix_only(root) else root


def build_plan(
    config: RunConfig, artifacts: RunArtifacts, targets: list[NormalizedTarget]
) -> list[CommandPlan]:
    if not targets:
        return []
    roots = sorted({_root_domain(t.host) for t in targets})
    plans: list[CommandPlan] = []
    timeout_minutes = max(1, config.command_wall_clock_s // 60)
    for index, root in enumerate(roots, start=1):
        prefix = artifacts.artifacts / f"amass_{index}"
        command: list[str] = [
            "amass", "enum",
            "-d", root,
            "-oA", str(prefix),
            "-timeout", str(timeout_minutes),
            "-nocolor",
        ]
        if config.amass_mode == "active":
            command.append("-active")
        # 'intel' is a separate amass subcommand; treat as active enum here.
        if config.amass_mode == "intel":
            command.append("-active")
        plans.append(
            CommandPlan(
                stage="amass",
                label=f"amass_{index}",
                command=command,
                artifacts=[prefix.with_suffix(".txt")],
            )
        )
    return plans


def parse_results(output_file: Path) -> tuple[list[Finding], list[str]]:
    """Read `<prefix>.txt` (one FQDN per line) and emit findings."""
    findings: list[Finding] = []
    fqdns: list[str] = []
    if not output_file.is_file():
        return findings, fqdns
    for line in output_file.read_text(encoding="utf-8").splitlines():
        host = line.strip()
        if not host or host.startswith("#"):
            continue
        fqdns.append(host)
    if fqdns:
        findings.append(
            Finding(
                stage="amass",
                kind="subdomain",
                target=fqdns[0],
                severity="info",
                title=f"Discovered {len(fqdns)} subdomains via amass",
                evidence=str(output_file),
            )
        )
    return findings, list(dict.fromkeys(fqdns))
