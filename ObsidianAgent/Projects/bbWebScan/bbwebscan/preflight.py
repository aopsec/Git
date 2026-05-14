import re
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from bbwebscan.models import RunConfig, ToolStatus

VERSION_ARGS: dict[str, list[str]] = {
    "httpx": ["-version"],
    "katana": ["-version"],
    "ffuf": ["-V"],
    "feroxbuster": ["--version"],
    "nuclei": ["-version"],
    "dirsearch": ["--version"],
    # [v0.5.0] amass v4.2.0: `amass -version` prints "v4.2.0" and the help
    # banner contains "OWASP Amass Project". kiterunner v1.0.2: `--version`
    # is unsupported (errors); use `help` to surface the kitebuilder-flavoured
    # banner instead.
    "amass": ["-version"],
    "kiterunner": ["help"],
    # [v0.5.3] Scrapy ships a `scrapy` console script via pip. `scrapy version`
    # prints "Scrapy 2.11.x". Identity regex anchors on the banner.
    "scrapy": ["version"],
}
# [FIX-BBW-08] Positive fingerprints for binaries commonly shadowed by Python shims
# or unrelated tools that share a name. Tools omitted here always report identity=None.
# IMPORTANT: each pattern must be discriminative — a binary that merely *prints its own
# name* must NOT match. For PD tools (httpx/katana/nuclei) we anchor on their org string
# or a multi-word tagline; ffuf has no known shadow shim so a name match is acceptable.
TOOL_IDENTITY: dict[str, re.Pattern[str]] = {
    "httpx": re.compile(r"projectdiscovery|fast and multi-purpose http", re.IGNORECASE),
    "katana": re.compile(r"projectdiscovery|next[- ]generation crawling", re.IGNORECASE),
    "nuclei": re.compile(
        r"projectdiscovery|template[- ]based vulnerability scanner", re.IGNORECASE
    ),
    "ffuf": re.compile(r"\bffuf\b", re.IGNORECASE),
    # [v0.5.0] Derived from observed banners on amass v4.2.0 / kiterunner v1.0.2.
    # amass `-version` output includes "OWASP Amass Project" in the banner ASCII.
    # kiterunner help references `kitebuilder` (its native wordlist format) and
    # `assetnote` (the upstream wordlist host) — neither is the binary's own name,
    # so a fake binary just printing "kiterunner" wouldn't pass.
    "amass": re.compile(r"OWASP|owaspamass", re.IGNORECASE),
    "kiterunner": re.compile(r"kitebuilder|assetnote", re.IGNORECASE),
    # [v0.5.3] `scrapy version` prints "Scrapy 2.11.0"; anchor on the banner
    # word plus a version number so a fake shim just printing "scrapy" fails.
    "scrapy": re.compile(r"scrapy\s+\d+\.\d+", re.IGNORECASE),
}
WORDLIST_TOOLS: set[str] = {"ffuf", "feroxbuster", "dirsearch"}
VERSION_PROBE_TIMEOUT_S: int = 10
_PROBE_TIMEOUT_RC: int = -1
_PROBE_OS_ERROR_RC: int = -2
# [FIX-BBW-D] Recon binaries land in these dirs by default. When a tool isn't on
# PATH, scanning these surfaces "installed but invisible" cases (e.g. fresh
# `cargo install feroxbuster` before the user's shell rc is updated).
_WELL_KNOWN_BIN_DIRS: tuple[Path, ...] = (
    Path.home() / "go" / "bin",
    Path.home() / ".cargo" / "bin",
    Path.home() / ".local" / "bin",
)


def collect_tool_inventory(config: RunConfig) -> list[ToolStatus]:
    extra = _compile_profile_fingerprints(config.profile_tool_identity)
    return inventory_tools(config.enabled_tools, extra_fingerprints=extra)


def inventory_tools(
    tool_names: list[str] | tuple[str, ...],
    *,
    extra_fingerprints: dict[str, re.Pattern[str]] | None = None,
) -> list[ToolStatus]:
    statuses: list[ToolStatus] = []
    for tool_name in tool_names:
        which_path, path_gap, shadowed_by = _resolve_tool_path(tool_name)
        # Probe whichever copy resolves first — prefer PATH so the result matches
        # what an actual scan would invoke.
        probe_target = which_path or path_gap
        version = detect_version(tool_name, probe_target)
        identity = detect_identity(
            tool_name, probe_target, extra_fingerprints=extra_fingerprints
        )
        statuses.append(
            ToolStatus(
                name=tool_name,
                required=True,
                found=which_path is not None,
                path=which_path or path_gap,
                version=version,
                note=_build_note(tool_name, which_path, identity, path_gap=path_gap),
                identity=identity,
                path_gap=path_gap,
                shadowed_by=shadowed_by,
            )
        )
    return statuses


def _resolve_tool_path(name: str) -> tuple[Path | None, Path | None, Path | None]:
    """Return ``(which_path, path_gap, shadowed_by)`` for a tool name.

    See FIX-BBW-D: detects "installed on disk but not on PATH" so doctor can
    point the operator at the missing PATH entry instead of a confusing
    "missing" report.
    """
    which_str = shutil.which(name)
    which_path = Path(which_str).resolve() if which_str else None

    disk_match: Path | None = None
    for bin_dir in _WELL_KNOWN_BIN_DIRS:
        candidate = bin_dir / name
        if candidate.is_file():
            disk_match = candidate.resolve()
            break

    if disk_match is None:
        return (which_path, None, None)
    if which_path is None:
        return (None, disk_match, None)
    if disk_match == which_path:
        return (which_path, None, None)
    # Both exist at different canonical paths — the well-known copy is shadowed.
    return (which_path, disk_match, which_path)


def _compile_profile_fingerprints(
    raw: dict[str, str],
) -> dict[str, re.Pattern[str]]:
    if not raw:
        return {}
    compiled: dict[str, re.Pattern[str]] = {}
    for tool, pattern in raw.items():
        try:
            compiled[tool] = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            raise ValueError(f"Invalid tool_identity regex for {tool}: {exc}") from exc
    return compiled


def _build_note(
    tool_name: str,
    tool_path: Path | None,
    identity: Literal["verified", "suspect"] | None,
    *,
    path_gap: Path | None = None,
) -> str | None:
    if tool_path is None and path_gap is not None:
        return (
            f"binary present at {path_gap} but not on PATH; "
            "run `bbwebscan doctor --fix-path` to add the missing dir"
        )
    if tool_path is None:
        return f"Install {tool_name} and re-run"
    if identity == "suspect":
        return (
            f"binary at {tool_path} does not match expected {tool_name} signature; "
            "verify it is the intended recon tool"
        )
    return None


def _probe(tool_path: Path, args: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            [str(tool_path), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=VERSION_PROBE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return (_PROBE_TIMEOUT_RC, "")
    except OSError:
        return (_PROBE_OS_ERROR_RC, "")
    return (completed.returncode, (completed.stdout or "") + (completed.stderr or ""))


def detect_version(tool_name: str, tool_path: Path | None) -> str | None:
    if tool_path is None:
        return None
    args = VERSION_ARGS.get(tool_name)
    if args is None:
        return None
    rc, output = _probe(tool_path, args)
    if rc == _PROBE_TIMEOUT_RC:
        return "probe-timeout"
    if rc == _PROBE_OS_ERROR_RC:
        return None
    stripped = output.strip()
    return stripped.splitlines()[0] if stripped else "unknown"


def detect_identity(
    tool_name: str,
    tool_path: Path | None,
    *,
    extra_fingerprints: dict[str, re.Pattern[str]] | None = None,
) -> Literal["verified", "suspect"] | None:
    if tool_path is None:
        return None
    # [FIX-BBW-A] Profile-supplied fingerprints override the built-in map.
    fingerprint = (extra_fingerprints or {}).get(tool_name) or TOOL_IDENTITY.get(tool_name)
    if fingerprint is None:
        return None
    # [FIX-BBW-08] Try VERSION_ARGS first; fall back to --help so binaries that
    # don't accept a version flag (Python shims, older releases) still get fingerprinted.
    probe_args = VERSION_ARGS.get(tool_name)
    if probe_args is not None:
        _, output = _probe(tool_path, probe_args)
        if fingerprint.search(output):
            return "verified"
    _, help_output = _probe(tool_path, ["--help"])
    if fingerprint.search(help_output):
        return "verified"
    return "suspect"


def validate_environment(config: RunConfig, statuses: list[ToolStatus]) -> list[str]:
    errors: list[str] = []
    # [FIX-BBW-06] Dry-run plans commands, so missing external scanners should not block it.
    if not config.dry_run or config.check_tools:
        errors.extend(
            f"Missing required tool: {status.name}" for status in statuses if not status.found
        )
    if (
        (not config.dry_run or config.check_tools)
        and any(tool in WORDLIST_TOOLS for tool in config.enabled_tools)
        and not config.wordlist.is_file()
    ):
        errors.append(f"Missing wordlist: {config.wordlist}")
    if config.auth.raw_request is not None and not config.auth.raw_request.is_file():
        errors.append(f"Missing raw request file: {config.auth.raw_request}")
    if config.strict_identity:
        # [FIX-BBW-B] Operator opt-in: promote suspect identity to a hard error.
        errors.extend(
            f"Suspect tool identity: {status.name} at {status.path} "
            f"({status.note or 'fingerprint mismatch'})"
            for status in statuses
            if status.identity == "suspect"
        )
    return errors
