#!/usr/bin/env python3
"""BLK7rch — Encrypted Arch Linux Pentest Installer built on archinstall.

Entry point for the ``blk7rch`` CLI and ``python -m blk7rch``.

Subcommands:
    install       Run the installer (interactive or unattended).
    config-init   Generate a starter JSON config file.
    self-test     Dry-run the installer with a pre-built test configuration.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from blk7rch.config.defaults import make_default_config
from blk7rch.config.loader import config_to_json, load_config, merge_cli_args
from blk7rch.config.schema import BLK7Config
from blk7rch.installer.core import BLK7Installer
from blk7rch.utils.logger import log


def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate subcommand handler."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "install":
        run_install(args)
    elif args.command == "config-init":
        config_init(args.output, args.profile)
    elif args.command == "self-test":
        run_self_test()
    else:
        parser.print_help()
        sys.exit(0)


def _build_parser() -> argparse.ArgumentParser:
    """Construct and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="blk7rch",
        description="BLK7rch — Encrypted Arch Linux Pentest Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  blk7rch install                          # Interactive TUI\n"
            "  blk7rch install --profile pentest        # Pentest preset, then TUI\n"
            "  blk7rch install --config blk7rch.json    # Fully unattended\n"
            "  blk7rch install --dry-run --profile pentest\n"
            "  blk7rch config-init pentest.json\n"
            "  blk7rch self-test\n"
        ),
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # ── install ──────────────────────────────────────────────────────────────
    p_install = sub.add_parser(
        "install",
        help="Run the installer",
        description="Perform an encrypted Arch Linux installation.",
    )
    p_install.add_argument(
        "--config", type=Path, metavar="FILE",
        help="Path to a JSON configuration file",
    )
    p_install.add_argument(
        "--creds", type=Path, metavar="FILE",
        help="Path to a separate credentials JSON file",
    )
    p_install.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="Simulate the installation without touching disks",
    )
    p_install.add_argument(
        "--unattended", action="store_true",
        help="Skip all interactive menus (requires --config)",
    )
    p_install.add_argument(
        "--profile", choices=["minimal", "core", "workstation", "pentest"],
        help="Override the installation profile",
    )
    p_install.add_argument(
        "--disk", type=str, metavar="DEVICE",
        help="Block device to install to, e.g. /dev/sda",
    )
    # ── config-init ──────────────────────────────────────────────────────────
    p_config = sub.add_parser(
        "config-init",
        help="Generate a starter JSON config file",
        description="Write a default BLK7rch configuration to a JSON file.",
    )
    p_config.add_argument(
        "output", nargs="?", default="blk7rch.json",
        metavar="OUTPUT",
        help="Output file path (default: blk7rch.json)",
    )
    p_config.add_argument(
        "--profile", default="workstation",
        choices=["minimal", "core", "workstation", "pentest"],
        help="Profile preset to use as the base (default: workstation)",
    )

    # ── self-test ─────────────────────────────────────────────────────────────
    sub.add_parser(
        "self-test",
        help="Dry-run the installer with a pentest preset",
        description="Run a full dry-run with the pentest profile to verify all code paths.",
    )

    return parser


def run_install(args: argparse.Namespace) -> None:
    """Handle the ``install`` subcommand.

    Parameters
    ----------
    args:
        Parsed CLI arguments from the ``install`` sub-parser.
    """
    dry_run: bool = getattr(args, "dry_run", False)

    # Load config
    if args.config:
        log.step(f"Loading config from {args.config}")
        cfg = load_config(args.config, creds_path=args.creds)
    else:
        profile = args.profile or "workstation"
        log.info(f"No config file specified — using '{profile}' defaults")
        cfg = make_default_config(profile)

    # Apply CLI overrides
    cfg = merge_cli_args(cfg, args)

    # Interactive menu (unless unattended)
    if not args.unattended and not dry_run:
        cfg = _run_interactive_menu(cfg)

    # Execute installation
    installer = BLK7Installer(cfg, dry_run=dry_run)
    installer.run()


def _run_interactive_menu(cfg: BLK7Config) -> BLK7Config:
    """Launch the archinstall-based TUI and return the updated config.

    Falls back gracefully if archinstall TUI is unavailable.

    Parameters
    ----------
    cfg:
        Initial configuration to pre-populate the menu.

    Returns
    -------
    BLK7Config
        Configuration as modified by the user through the menu.
    """
    try:
        from blk7rch.tui.menu import BLK7Menu

        data_store: dict = {}
        menu = BLK7Menu(data_store, cfg)
        menu.run()

        # Merge any changes made in the menu back into cfg
        for key in cfg.__dataclass_fields__:
            if key in data_store:
                setattr(cfg, key, data_store[key])

        return cfg
    except (ImportError, AttributeError, TypeError, RuntimeError) as exc:
        # TUI may be absent (ImportError), archinstall API may differ (AttributeError/TypeError),
        # or curses may fail in non-interactive environments (RuntimeError).
        log.warn(f"Interactive menu unavailable ({exc}) — proceeding with current config")
        return cfg


def config_init(output: str | Path, profile: str = "workstation") -> None:
    """Write a default BLK7Config as a JSON file.

    Parameters
    ----------
    output:
        Destination file path.
    profile:
        Profile preset to use as the base configuration.
    """
    try:
        output_path = Path(output)
        cfg = make_default_config(profile)
        json_str = config_to_json(cfg, include_passwords=False)
        output_path.write_text(json_str)
        log.ok(f"Config written to {output_path}")
        print(json_str)
    except Exception as exc:  # noqa: BLE001 — catch-all for config-init error report
        log.error(f"config-init failed: {exc}")
        sys.exit(1)


def run_self_test() -> None:
    """Run a full dry-run with the pentest profile.

    All 21 feature code paths are exercised with ``dry_run=True`` so no disk
    operations are performed.  Exits with code 0 on success, 1 on failure.
    """
    log.step("self-test: running dry-run with pentest profile")

    cfg = make_default_config("pentest")
    cfg.disk = "/dev/sda"
    cfg.hostname = "blk7test"
    cfg.username = "testuser"
    cfg.encryption_password = "testpass"
    cfg.user_password = "testpass"
    cfg.root_password = "testpass"

    try:
        installer = BLK7Installer(cfg, dry_run=True)
        installer.run()
        log.ok("self-test: PASSED — all phases completed in dry-run mode")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001 — catch-all for self-test report
        log.error(f"self-test: FAILED — {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
