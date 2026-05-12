import argparse

from bbwebscan.config import SUPPORTED_TOOLS, load_profile
from bbwebscan.installer import persist_path_in_shell_rc
from bbwebscan.models import ToolStatus
from bbwebscan.preflight import _compile_profile_fingerprints, inventory_tools

INSTALL_HINTS: dict[str, str] = {
    "httpx": "go install github.com/projectdiscovery/httpx/cmd/httpx@latest",
    "katana": "go install github.com/projectdiscovery/katana/cmd/katana@latest",
    "nuclei": "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    "ffuf": "go install github.com/ffuf/ffuf/v2@latest",
    "feroxbuster": "cargo install --locked --force feroxbuster",
    "arjun": "pipx install arjun",
    "dirsearch": "pipx install dirsearch  # or run `bbwebscan install`",
    # [v0.5.0] Verified upstream paths (curl -sI returned 200 during install).
    # amass package layout: github.com/owasp-amass/amass/v4 (cmd/amass).
    # kiterunner package layout: github.com/assetnote/kiterunner (cmd/kiterunner).
    "amass": "go install -v github.com/owasp-amass/amass/v4/...@master",
    "kiterunner": "go install github.com/assetnote/kiterunner/cmd/kiterunner@latest",
}

_NAME_WIDTH = 12


def format_report(statuses: list[ToolStatus], *, strict_identity: bool = False) -> str:
    lines = ["bbwebscan doctor — toolchain readiness", ""]
    for status in statuses:
        symbol, label = _classify(status)
        version = status.version or "n/a"
        path = status.path or "not on PATH"
        lines.append(f"  {symbol} {status.name:<{_NAME_WIDTH}} {label:<10} {version}")
        if status.path_gap is not None and not status.found:
            lines.append(f"      → on disk at {status.path_gap} (not on PATH)")
            lines.append(
                "        run `bbwebscan doctor --fix-path` to add the bin dir to your shell"
            )
        elif status.path_gap is not None and status.shadowed_by is not None:
            lines.append(
                f"      → {status.shadowed_by} is on PATH first, "
                f"shadowing {status.path_gap}"
            )
            lines.append(
                "        if the shallow copy is wrong, remove it or prepend the deeper "
                "dir on PATH"
            )
        elif not status.found:
            hint = INSTALL_HINTS.get(status.name)
            if hint:
                lines.append(f"      → install: {hint}")
        elif status.identity == "suspect":
            note = status.note or "binary did not match expected fingerprint"
            lines.append(f"      → suspect: {note}")
        elif status.path is not None:
            lines.append(f"      path: {path}")
    summary = _summary_line(statuses, strict_identity=strict_identity)
    lines.extend(["", summary])
    return "\n".join(lines)


def _classify(status: ToolStatus) -> tuple[str, str]:
    if not status.found and status.path_gap is not None:
        return ("⚠", "on-disk")
    if not status.found:
        return ("✗", "missing")
    if status.identity == "suspect":
        return ("?", "suspect")
    if status.path_gap is not None and status.shadowed_by is not None:
        return ("⚠", "shadowed")
    return ("✓", "found")


def _summary_line(statuses: list[ToolStatus], *, strict_identity: bool) -> str:
    missing = [s.name for s in statuses if not s.found and s.path_gap is None]
    path_gap = [s.name for s in statuses if not s.found and s.path_gap is not None]
    shadowed = [
        s.name for s in statuses if s.found and s.shadowed_by is not None
    ]
    suspect = [
        s.name for s in statuses
        if s.found and s.identity == "suspect" and s.shadowed_by is None
    ]
    parts: list[str] = []
    if missing:
        parts.append(f"{len(missing)} missing ({', '.join(missing)})")
    if path_gap:
        parts.append(f"{len(path_gap)} path-gap ({', '.join(path_gap)})")
    if shadowed:
        parts.append(f"{len(shadowed)} shadowed ({', '.join(shadowed)})")
    if suspect:
        parts.append(f"{len(suspect)} suspect ({', '.join(suspect)})")
    if not parts:
        return "All tools ready."
    fixes: list[str] = []
    if path_gap:
        fixes.append("`bbwebscan doctor --fix-path` to add bin dirs")
    if missing:
        fixes.append("`bbwebscan install` to install missing tools")
    suffix = (" — run " + " or ".join(fixes)) if fixes else ""
    strict_note = " (strict-identity will fail)" if strict_identity and suspect else ""
    return "Issues: " + "; ".join(parts) + suffix + strict_note


def doctor_exit_code(
    statuses: list[ToolStatus], *, strict_identity: bool = False
) -> int:
    if any(not s.found for s in statuses):
        return 2
    if strict_identity and any(s.identity == "suspect" for s in statuses):
        return 2
    return 0


def run_doctor(args: argparse.Namespace) -> int:
    if getattr(args, "fix_path", False):
        return _run_fix_path()
    if args.profile:
        profile = load_profile(args.profile)
        tools = list(profile.enabled_tools) or list(SUPPORTED_TOOLS)
        extra = _compile_profile_fingerprints(profile.tool_identity)
    else:
        tools = list(SUPPORTED_TOOLS)
        extra = {}
    statuses = inventory_tools(tools, extra_fingerprints=extra)
    print(format_report(statuses, strict_identity=args.strict_identity))
    return doctor_exit_code(statuses, strict_identity=args.strict_identity)


def _run_fix_path() -> int:
    rc_path, added = persist_path_in_shell_rc()
    if not added:
        print(f"[bbwebscan doctor --fix-path] {rc_path} already configured; nothing to do.")
        return 0
    print(f"[bbwebscan doctor --fix-path] updated {rc_path}")
    print(f"  prepended: {', '.join(str(p) for p in added)}")
    print("Open a new shell or run `source` your rc file to pick up the changes.")
    return 0
