import re

import pytest

from bbwebscan.cli import _rewrite_smart_default, build_parser, main


def test_rewrite_smart_default_passthrough_for_subcommand() -> None:
    assert _rewrite_smart_default(["scan", "--target", "x.com"]) == [
        "scan", "--target", "x.com"
    ]
    assert _rewrite_smart_default(["doctor"]) == ["doctor"]
    assert _rewrite_smart_default(["menu"]) == ["menu"]


def test_rewrite_smart_default_passthrough_for_help() -> None:
    assert _rewrite_smart_default(["-h"]) == ["-h"]
    assert _rewrite_smart_default(["--help"]) == ["--help"]


def test_rewrite_smart_default_inserts_scan_for_flat_flags() -> None:
    """Back-compat: `bbwebscan --target x.com` should still work."""
    assert _rewrite_smart_default(["--target", "x.com", "--dry-run"]) == [
        "scan", "--target", "x.com", "--dry-run",
    ]


def test_rewrite_smart_default_promotes_positional_host() -> None:
    """`bbwebscan example.com` → `bbwebscan scan --target example.com`."""
    assert _rewrite_smart_default(["example.com", "--dry-run"]) == [
        "scan", "--target", "example.com", "--dry-run",
    ]


def test_rewrite_smart_default_empty_argv() -> None:
    assert _rewrite_smart_default([]) == []


def test_build_parser_supports_all_subcommands() -> None:
    parser = build_parser()
    # Round-trip each subcommand through parse_args to assert the layout is wired.
    args = parser.parse_args(["scan", "--target", "x.com"])
    assert args.command == "scan"
    args = parser.parse_args(["install", "--dry-run"])
    assert args.command == "install"
    assert args.dry_run is True
    args = parser.parse_args(["doctor", "--strict-identity"])
    assert args.command == "doctor"
    assert args.strict_identity is True
    args = parser.parse_args(["init", "demo", "--target", "x.com"])
    assert args.command == "init"
    assert args.program_name == "demo"
    args = parser.parse_args(["menu"])
    assert args.command == "menu"


def test_main_with_no_args_dispatches_to_menu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[bool] = []

    def fake_menu() -> int:
        called.append(True)
        return 0

    monkeypatch.setattr("bbwebscan.cli.run_menu", fake_menu)
    rc = main([])
    assert rc == 0
    assert called == [True]


@pytest.mark.parametrize("subcommand,extra", [
    ("install", ["--dry-run"]),
    ("doctor", []),
    ("init", ["myprog", "--target", "x.example.com"]),
])
def test_ack_authorized_accepted_on_every_subcommand(
    subcommand: str, extra: list[str],
) -> None:
    """v0.4.2 (FIX-BBW-F): --ack-authorized is silently accepted on every
    subcommand even though only `scan` consumes it, so users muscle-memorying
    it everywhere don't hit a confusing argparse error."""
    parser = build_parser()
    args = parser.parse_args([subcommand, "--ack-authorized", *extra])
    assert args.command == subcommand
    assert args.ack_authorized is True


def test_ack_authorized_default_false_when_omitted() -> None:
    parser = build_parser()
    args = parser.parse_args(["doctor"])
    assert args.ack_authorized is False


def test_version_flag_prints_version_and_exits_0(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """v0.4.3 (Item 1): --version is a root-parser flag; prints `bbwebscan X.Y.Z`."""
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("bbwebscan ")
    # Reject "0.0.0+local" fallback in the asserting regex - we want a real version.
    assert re.match(r"^bbwebscan \d+\.\d+\.\d+", out), f"unexpected version line: {out!r}"
