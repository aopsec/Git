import argparse
import sys
from collections.abc import Callable
from datetime import UTC, datetime

from bbwebscan import __version__
from bbwebscan.config import build_run_config
from bbwebscan.doctor import run_doctor
from bbwebscan.history import run_compare, run_history, run_show
from bbwebscan.init_profile import run_init
from bbwebscan.installer import run_installer
from bbwebscan.menu import run_menu
from bbwebscan.pipeline import execute_scan
from bbwebscan.welcome import print_welcome

SUBCOMMANDS: tuple[str, ...] = (
    "scan", "install", "doctor", "init", "history", "show", "compare", "menu",
)


def _add_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile")
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--input")
    parser.add_argument("--mode", choices=["safe", "aggressive"])
    parser.add_argument("--ack-authorized", action="store_true")
    parser.add_argument("--header", action="append", default=[])
    parser.add_argument("--cookie", action="append", default=[])
    parser.add_argument("--raw-request")
    parser.add_argument("--output-dir")
    parser.add_argument("--wordlist")
    parser.add_argument("--check-tools", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--enable-tool", action="append", default=[])
    parser.add_argument("--disable-tool", action="append", default=[])
    parser.add_argument("--threads", type=int)
    parser.add_argument("--rate", type=int)
    parser.add_argument("--tool-timeout", type=int, dest="tool_timeout",
                        help="Per-tool timeout in seconds (default 15)")
    parser.add_argument("--cmd-timeout", type=int, dest="cmd_timeout",
                        help="Subprocess wall-clock timeout in seconds (default 900)")
    parser.add_argument("--max-attempts", type=int, dest="max_attempts",
                        help="Retry attempts on transient failure (default 1)")
    parser.add_argument("--backoff-s", type=float, dest="backoff_s",
                        help="Retry backoff base in seconds (default 2.0)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress per-stage progress output")
    parser.add_argument("--strict-identity", action="store_true",
                        help="Fail if any tool fingerprint is suspect")
    parser.add_argument(
        "--severity",
        choices=["info", "low", "medium", "high", "critical"],
        default="info",
        help="Drop findings below this severity; exit 3 if any meet the threshold",
    )
    parser.add_argument(
        "--check-dns", dest="check_dns", action="store_true",
        help="Resolve each target host before scanning; non-fatal note in summary on failure",
    )
    parser.add_argument(
        "--enumerate-subdomains", dest="enumerate_subdomains", action="store_true",
        help="Run amass before httpx to enumerate subdomains from each target's root domain",
    )
    parser.add_argument(
        "--amass-mode", dest="amass_mode",
        choices=["passive", "active", "intel"], default="passive",
        help=(
            "amass enum mode (default: passive). active and intel make "
            "detectable DNS queries; both require --ack-authorized."
        ),
    )
    parser.add_argument(
        "--api-discovery", dest="api_discovery", action="store_true",
        help="Run kiterunner alongside ffuf in the discovery stage for API-shaped targets",
    )
    parser.add_argument(
        "--scrapy-deep", dest="scrapy_deep", action="store_true",
        help=(
            "Enable Scrapy sensitive-data extractors (secrets/credentials via "
            "vendored ruleset). Default off; emits findings only at evidence "
            "prefixes (SHA-256), never raw values."
        ),
    )
    parser.add_argument(
        "--scrapy-max-depth", dest="scrapy_max_depth",
        type=int, choices=range(1, 6), default=2,
        help="Scrapy max crawl depth (1-5, default 2)",
    )
    parser.add_argument(
        "--scrapy-js-render", dest="scrapy_js_render", action="store_true",
        help=(
            "Render JavaScript in the Scrapy stage via scrapy-playwright. "
            "Requires the [js] extra and a Chromium install."
        ),
    )
    parser.set_defaults(run_label=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bbwebscan",
        description="Scope-aware bug bounty web recon orchestrator",
    )
    parser.add_argument(
        "--version", action="version", version=f"bbwebscan {__version__}",
    )
    sub = parser.add_subparsers(dest="command")

    scan = sub.add_parser("scan", help="Run a recon scan")
    _add_scan_args(scan)

    install = sub.add_parser("install", help="Install missing recon tools")
    install.add_argument("--dry-run", action="store_true")
    # [FIX-BBW-D] persist-path is on by default; the bash installer adds the recon
    # bin dirs to the user's shell rc unless --no-persist-path is passed.
    install.add_argument(
        "--no-persist-path", dest="persist_path", action="store_false", default=True,
        help="Skip appending recon bin dirs to your shell rc",
    )
    install.add_argument("--update-nuclei-templates", action="store_true")
    install.add_argument("--installer", help="Path to bbScan_Installer.sh")
    install.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress cargo/go compile output; keep status lines and errors only",
    )

    doctor = sub.add_parser("doctor", help="Inspect toolchain readiness")
    doctor.add_argument("--profile", help="Use profile-supplied tool list")
    doctor.add_argument("--strict-identity", action="store_true")
    doctor.add_argument(
        "--fix-path", action="store_true",
        help="Prepend recon bin dirs to your shell rc (idempotent)",
    )

    init = sub.add_parser("init", help="Scaffold a program profile YAML")
    init.add_argument("program_name")
    init.add_argument("--target", action="append", default=[])
    init.add_argument("--out", help="Output path (default: profiles/<name>.yaml)")
    init.add_argument("--force", action="store_true")

    # [v0.4.3 Items 3+4] history / show / compare for past run inspection.
    history = sub.add_parser("history", help="List past runs newest-first")
    history.add_argument("--limit", type=int, default=20)
    history.add_argument("--runs-dir", help="Override runs/ directory (default: runs)")

    show = sub.add_parser("show", help="Print summary.md for a past run")
    show.add_argument("run_dir")

    compare = sub.add_parser("compare", help="Diff findings between two past runs")
    compare.add_argument("run_a")
    compare.add_argument("run_b")

    menu = sub.add_parser("menu", help="Open the interactive terminal menu")

    # [FIX-BBW-F] Accept --ack-authorized as a no-op on every non-scan subparser
    # so users muscle-memorying it from `scan` don't hit a confusing argparse error.
    for parity_parser in (install, doctor, init, history, show, compare, menu):
        parity_parser.add_argument(
            "--ack-authorized",
            action="store_true",
            help="Accepted for parity with `scan`; has no effect on this subcommand",
        )

    return parser


def _rewrite_smart_default(argv: list[str]) -> list[str]:
    """Insert default subcommand when the user invokes flat-CLI style.

    - `bbwebscan example.com [...]` → `bbwebscan scan --target example.com [...]`.
    - `bbwebscan --target example.com [...]` → `bbwebscan scan --target ...`.
    - `bbwebscan -h` / `bbwebscan --help` are passed through to the root parser.
    - Subcommand invocations are passed through unchanged.
    """
    if not argv:
        return argv
    first = argv[0]
    if first in SUBCOMMANDS:
        return argv
    if first in {"-h", "--help", "--version"}:
        return argv
    if first.startswith("-"):
        # Flat-CLI back-compat: no subcommand, but starts with a flag → assume `scan`.
        return ["scan", *argv]
    if "." in first:
        return ["scan", "--target", first, *argv[1:]]
    return argv


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(argv if argv is not None else sys.argv[1:])
    rewritten = _rewrite_smart_default(raw_argv)
    parser = build_parser()
    args = parser.parse_args(rewritten)
    handler = _COMMANDS.get(args.command, cmd_welcome)
    return handler(args, parser)


def cmd_scan(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        config = build_run_config(args)
    except (FileNotFoundError, ValueError) as exc:
        # [FIX-BBW-05] Keep user/input errors actionable without Python tracebacks.
        parser.error(str(exc))
    return execute_scan(config)


def cmd_install(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        return run_installer(args)
    except FileNotFoundError as exc:
        parser.error(str(exc))


def cmd_doctor(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        return run_doctor(args)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))


def cmd_init(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        return run_init(args)
    except (FileExistsError, ValueError) as exc:
        parser.error(str(exc))


def cmd_welcome(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    print_welcome()
    return 0


def cmd_menu(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    del args, parser
    return run_menu()


def cmd_history(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        return run_history(args)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))


def cmd_show(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        return run_show(args)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))


def cmd_compare(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        return run_compare(args)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))


_COMMANDS: dict[str | None, Callable[[argparse.Namespace, argparse.ArgumentParser], int]] = {
    "scan": cmd_scan,
    "install": cmd_install,
    "doctor": cmd_doctor,
    "init": cmd_init,
    "history": cmd_history,
    "show": cmd_show,
    "compare": cmd_compare,
    "menu": cmd_menu,
    None: cmd_menu,
}
