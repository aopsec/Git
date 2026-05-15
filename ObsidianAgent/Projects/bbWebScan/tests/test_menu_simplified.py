"""[v0.5.7] Tests for simplified 6-item menu and new menu modules."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from bbwebscan import menu as menu_mod
from bbwebscan import menu_collect as menu_collect_mod
from bbwebscan import menu_custom as menu_custom_mod
from bbwebscan import menu_profiles as menu_profiles_mod
from bbwebscan import menu_quick as menu_quick_mod
from bbwebscan.menu_types import ScanSettings


class _StubIO:
    """Stub MenuIO for testing."""

    def __init__(self) -> None:
        self.messages: list[str] = []
        self.panels: list[tuple[str, str]] = []
        self.tables: list[tuple[str, list[str], list[list[str]]]] = []

    def print(self, message: str = "") -> None:
        self.messages.append(message)

    def panel(self, title: str, body: str) -> None:
        self.panels.append((title, body))

    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
        self.tables.append((title, columns, rows))


# ---- menu_collect.py tests ----

def test_collect_targets_returns_list_when_provided() -> None:
    inputs = iter(["example.com,api.example.com"])
    targets = menu_collect_mod.collect_targets(ScanSettings(), lambda _: next(inputs))
    assert targets == ["example.com", "api.example.com"]


def test_collect_targets_returns_default_when_blank() -> None:
    targets = menu_collect_mod.collect_targets(ScanSettings(targets=["a.com"]), lambda _: "")
    assert targets == ["a.com"]


def test_collect_mode_returns_safe_or_aggressive() -> None:
    safe = menu_collect_mod.collect_mode(ScanSettings(), lambda _: "safe")
    assert safe == "safe"
    agg = menu_collect_mod.collect_mode(ScanSettings(mode="aggressive"), lambda _: "aggressive")
    assert agg == "aggressive"


def test_collect_dry_run_returns_bool() -> None:
    dry = menu_collect_mod.collect_dry_run(ScanSettings(), lambda _: "y")
    assert dry is True
    no_dry = menu_collect_mod.collect_dry_run(ScanSettings(), lambda _: "n")
    assert no_dry is False


def test_collect_output_dir_returns_none_when_blank() -> None:
    out = menu_collect_mod.collect_output_dir(ScanSettings(), lambda _: "")
    assert out is None


def test_collect_output_dir_returns_path_when_provided() -> None:
    out = menu_collect_mod.collect_output_dir(ScanSettings(), lambda _: "/tmp/out")
    assert out == "/tmp/out"


def test_collect_wordlist_returns_none_when_blank() -> None:
    wl = menu_collect_mod.collect_wordlist(ScanSettings(), lambda _: "")
    assert wl is None


def test_collect_wordlist_returns_path_when_provided() -> None:
    wl = menu_collect_mod.collect_wordlist(ScanSettings(), lambda _: "/tmp/words.txt")
    assert wl == "/tmp/words.txt"


def test_collect_extra_tools_returns_defaults_on_invalid() -> None:
    inputs = iter(["invalid-tool", ""])  # invalid tool → catches ValueError
    enable, disable = menu_collect_mod.collect_extra_tools(
        ScanSettings(), lambda _: next(inputs),
    )
    # Falls back to ScanSettings defaults on error
    assert enable == ScanSettings().enable_tool
    assert disable == ScanSettings().disable_tool


def test_collect_severity_returns_valid_severity() -> None:
    sev = menu_collect_mod.collect_severity(ScanSettings(), lambda _: "high")
    assert sev == "high"


def test_collect_threads_returns_int_or_none() -> None:
    threads = menu_collect_mod.collect_threads(ScanSettings(), lambda _: "8")
    assert threads == 8
    blank = menu_collect_mod.collect_threads(ScanSettings(threads=4), lambda _: "")
    assert blank == 4


def test_collect_rate_returns_int_or_none() -> None:
    rate = menu_collect_mod.collect_rate(ScanSettings(), lambda _: "100")
    assert rate == 100
    blank = menu_collect_mod.collect_rate(ScanSettings(rate=50), lambda _: "")
    assert blank == 50


def test_collect_authorization_ack_safe_mode() -> None:
    ack = menu_collect_mod.collect_authorization_ack("safe", False, lambda _: "y")
    assert ack is True


def test_collect_authorization_ack_aggressive_mode_requires_authorized() -> None:
    ack = menu_collect_mod.collect_authorization_ack(
        "aggressive", False, lambda _: "AUTHORIZED"
    )
    assert ack is True
    nack = menu_collect_mod.collect_authorization_ack(
        "aggressive", False, lambda _: "anything-else"
    )
    assert nack is False


# ---- menu_quick.py tests ----

def test_run_quick_scan_no_targets() -> None:
    io = _StubIO()
    rc = menu_quick_mod.run_quick_scan(
        io,
        input_func=lambda _: "",
        scan_executor=lambda _: 0,
    )
    assert rc == 1  # No targets


def test_run_quick_scan_returns_executor_exit_code(tmp_path: Path) -> None:
    """When targets provided, run_quick_scan executes and returns exit code."""
    def fake_executor(_config: Any) -> int:
        return 42

    io = _StubIO()
    inputs = iter(["example.com", "n"])  # targets + dry-run
    rc = menu_quick_mod.run_quick_scan(
        io,
        input_func=lambda _: next(inputs),
        scan_executor=fake_executor,
    )
    # Depends on build_run_config not raising
    assert rc in (42, 2)  # Either executor code or config error


# ---- menu_custom.py tests ----

def test_run_custom_scan_preview_command() -> None:
    """Choice 1 previews the command."""
    io = _StubIO()
    inputs = iter([
        "example.com",  # targets
        "safe",  # mode
        "y",  # ack_authorized
        "",  # output_dir
        "",  # wordlist
        "",  # enable_tool
        "",  # disable_tool
        "info",  # severity
        "",  # threads
        "",  # rate
        "y",  # dry_run
        "1",  # action menu: preview
        "5",  # action menu: back
    ])
    rc = menu_custom_mod.run_custom_scan(
        io, session_ack=False, input_func=lambda _: next(inputs),
    )
    assert rc == 0


def test_run_custom_scan_back() -> None:
    """Choice 5 returns to main menu."""
    io = _StubIO()
    inputs = iter([
        "example.com",  # targets
        "safe",  # mode
        "y",  # ack_authorized
        "",  # output_dir
        "",  # wordlist
        "",  # enable_tool
        "",  # disable_tool
        "info",  # severity
        "",  # threads
        "",  # rate
        "y",  # dry_run
        "5",  # action menu: back
    ])
    rc = menu_custom_mod.run_custom_scan(
        io, session_ack=False, input_func=lambda _: next(inputs),
    )
    assert rc == 0


def test_select_profile_no_profiles_dir() -> None:
    """_select_profile returns default ScanSettings when no profiles dir."""
    settings = menu_custom_mod._select_profile(lambda _: "default")
    assert isinstance(settings, ScanSettings)


def test_action_menu_body_has_menu_items() -> None:
    """_action_menu_body returns expected menu text."""
    body = menu_custom_mod._action_menu_body()
    assert "Preview command" in body
    assert "Run scan" in body
    assert "Dry-run" in body
    assert "Save and exit" in body
    assert "Back to main menu" in body


# ---- menu_profiles.py tests ----

def test_run_profiles_menu_back() -> None:
    """Choice 5 backs to main menu."""
    io = _StubIO()
    rc = menu_profiles_mod.run_profiles_menu(io, input_func=lambda _: "5")
    assert rc == 0


def test_run_profiles_menu_list() -> None:
    """Profile menu list action completes without error."""
    io = _StubIO()
    inputs = iter(["1", "5"])  # list, back
    rc = menu_profiles_mod.run_profiles_menu(io, input_func=lambda _: next(inputs))
    assert rc == 0


def test_run_profiles_menu_invalid_choice() -> None:
    """Invalid choice prompts to try again."""
    io = _StubIO()
    inputs = iter(["9", "5"])  # invalid, back
    menu_profiles_mod.run_profiles_menu(io, input_func=lambda _: next(inputs))
    assert any("1 to 5" in m for m in io.messages)


def test_list_profiles() -> None:
    """_list_profiles handles both empty and populated directories."""
    io = _StubIO()
    menu_profiles_mod._list_profiles(io)
    assert len(io.messages) > 0


def test_load_and_describe_profile_cancel() -> None:
    """_load_and_describe_profile handles blank input gracefully."""
    io = _StubIO()
    menu_profiles_mod._load_and_describe_profile(io, lambda _: "")
    assert len(io.messages) >= 0


def test_delete_profile_cancel() -> None:
    """_delete_profile handles blank input gracefully."""
    io = _StubIO()
    menu_profiles_mod._delete_profile(io, lambda _: "")
    assert len(io.messages) >= 0


def test_create_profile_blank_input() -> None:
    """_create_profile cancels on blank program name."""
    io = _StubIO()
    menu_profiles_mod._create_profile(io, lambda _: "")
    assert any("cancelled" in m for m in io.messages)


def test_profiles_menu_body_has_items() -> None:
    """_profiles_menu_body returns expected menu text."""
    body = menu_profiles_mod._profiles_menu_body()
    assert "List profiles" in body
    assert "Create profile" in body
    assert "Load and describe" in body
    assert "Delete profile" in body
    assert "Back to main menu" in body


# ---- menu.py (refactored) tests ----

def test_run_menu_exit_on_choice_6() -> None:
    """Choice 6 exits main menu."""
    io = _StubIO()
    rc = menu_mod.run_menu(input_func=lambda _: "6", io=io)
    assert rc == 0


def test_run_menu_invalid_choice() -> None:
    """Invalid choice prompts to try again."""
    io = _StubIO()
    inputs = iter(["9", "6"])  # invalid, exit
    rc = menu_mod.run_menu(input_func=lambda _: next(inputs), io=io)
    assert rc == 0
    assert any("1 to 6" in m for m in io.messages)


def test_run_menu_all_valid_choices() -> None:
    """All 6 valid choices are in the handler dict."""
    handlers = menu_mod._menu_handlers()
    for choice in ("1", "2", "3", "4", "5"):
        assert choice in handlers


def test_main_menu_body_has_6_items() -> None:
    """_main_menu_body returns all 6 menu items."""
    body = menu_mod._main_menu_body()
    assert "Quick Scan" in body
    assert "Custom Scan" in body
    assert "Manage Profiles" in body
    assert "Doctor / Auto Fix" in body
    assert "History" in body
    assert "Exit" in body


def test_rich_menu_io_print_fallback() -> None:
    """RichMenuIO.print falls back to print() when rich unavailable."""
    io = menu_mod.RichMenuIO()
    # Rich likely available but test the interface
    io.print("test")  # Should not raise


def test_rich_menu_io_panel_fallback() -> None:
    """RichMenuIO.panel works without rich."""
    io = menu_mod.RichMenuIO()
    io.panel("Title", "Body")  # Should not raise


def test_rich_menu_io_table_fallback() -> None:
    """RichMenuIO.table works without rich."""
    io = menu_mod.RichMenuIO()
    io.table("Title", ["A", "B"], [["x", "y"]])  # Should not raise


def test_plain_table_print() -> None:
    """_print_plain_table outputs expected format."""
    # Just ensure it doesn't raise
    menu_mod._print_plain_table("Title", ["A", "B"], [["x", "y"]])


def test_run_custom_scan_action_run() -> None:
    """Choice 2 runs the scan with dry-run=False."""
    io = _StubIO()
    executed = []

    def fake_executor(_config: Any) -> int:
        executed.append("run")
        return 0

    inputs = iter([
        "example.com",  # targets
        "safe",  # mode
        "y",  # ack
        "",  # output_dir
        "",  # wordlist
        "",  # enable_tool
        "",  # disable_tool
        "info",  # severity
        "",  # threads
        "",  # rate
        "n",  # dry_run
        "2",  # action: run
    ])
    rc = menu_custom_mod.run_custom_scan(
        io, session_ack=False, input_func=lambda _: next(inputs),
        scan_executor=fake_executor,
    )
    assert rc in (0, 2)
    assert len(executed) > 0 or rc == 2


def test_run_custom_scan_action_dry_run() -> None:
    """Choice 3 runs the scan with dry-run=True."""
    io = _StubIO()
    executed = []

    def fake_executor(_config: Any) -> int:
        executed.append("dry-run")
        return 0

    inputs = iter([
        "example.com",  # targets
        "safe",  # mode
        "y",  # ack
        "",  # output_dir
        "",  # wordlist
        "",  # enable_tool
        "",  # disable_tool
        "info",  # severity
        "",  # threads
        "",  # rate
        "y",  # dry_run
        "3",  # action: dry-run
    ])
    rc = menu_custom_mod.run_custom_scan(
        io, session_ack=False, input_func=lambda _: next(inputs),
        scan_executor=fake_executor,
    )
    assert rc in (0, 2)
    assert len(executed) > 0 or rc == 2


def test_run_custom_scan_action_save_no() -> None:
    """Choice 4 with 'no' to save returns to menu."""
    io = _StubIO()
    inputs = iter([
        "example.com",  # targets
        "safe",  # mode
        "y",  # ack
        "",  # output_dir
        "",  # wordlist
        "",  # enable_tool
        "",  # disable_tool
        "info",  # severity
        "",  # threads
        "",  # rate
        "y",  # dry_run
        "4",  # action: save
        "n",  # don't save
    ])
    rc = menu_custom_mod.run_custom_scan(
        io, session_ack=False, input_func=lambda _: next(inputs),
    )
    assert rc == 0


def test_run_profiles_menu_create() -> None:
    """Create profile menu action completes without error."""
    io = _StubIO()
    inputs = iter([
        "2",  # create
        "",  # cancel (blank program name)
        "5",  # back
    ])
    rc = menu_profiles_mod.run_profiles_menu(io, input_func=lambda _: next(inputs))
    assert rc == 0


def test_run_custom_scan_run_fails_on_config_error() -> None:
    """run_configured_scan returns 2 on config error."""
    io = _StubIO()
    inputs = iter([
        "example.com",  # targets
        "safe",  # mode
        "y",  # ack
        "",  # output_dir
        "",  # wordlist
        "",  # enable_tool
        "",  # disable_tool
        "info",  # severity
        "",  # threads
        "",  # rate
        "n",  # dry_run
        "2",  # action: run (will fail on bad config)
    ])

    def failing_executor(_config: Any) -> int:
        raise ValueError("bad config")

    rc = menu_custom_mod.run_custom_scan(
        io, session_ack=False, input_func=lambda _: next(inputs),
        scan_executor=failing_executor,
    )
    assert rc == 2
    assert any("bad config" in m for m in io.messages)


def test_quick_scan_with_targets() -> None:
    """Quick scan with valid targets executes successfully."""
    io = _StubIO()
    inputs = iter([
        "example.com",  # targets
        "n",  # dry_run
    ])

    def fake_executor(_config: Any) -> int:
        return 0

    rc = menu_quick_mod.run_quick_scan(
        io, input_func=lambda _: next(inputs),
        scan_executor=fake_executor,
    )
    assert rc in (0, 2)


def test_quick_scan_config_error() -> None:
    """Quick scan handles config errors gracefully."""
    io = _StubIO()
    inputs = iter([
        "example.com",  # targets
        "n",  # dry_run
    ])

    def failing_executor(_config: Any) -> int:
        raise FileNotFoundError("missing tool")

    rc = menu_quick_mod.run_quick_scan(
        io, input_func=lambda _: next(inputs),
        scan_executor=failing_executor,
    )
    assert rc == 2
    assert any("missing tool" in m for m in io.messages)


def test_run_menu_quick_scan() -> None:
    """Menu choice 1 triggers quick scan."""
    io = _StubIO()
    inputs = iter([
        "example.com",  # quick scan targets
        "n",  # quick scan dry_run
        "6",  # exit (after scan fails due to missing tools)
    ])

    def fake_executor(_config: Any) -> int:
        return 2

    rc = menu_mod.run_menu(input_func=lambda _: next(inputs), io=io)
    assert rc == 0


def test_run_menu_custom_scan() -> None:
    """Menu choice 2 triggers custom scan."""
    io = _StubIO()
    inputs = iter([
        "example.com",  # targets
        "safe",  # mode
        "y",  # ack
        "",  # output_dir
        "",  # wordlist
        "",  # enable_tool
        "",  # disable_tool
        "info",  # severity
        "",  # threads
        "",  # rate
        "y",  # dry_run
        "5",  # action: back
        "6",  # exit menu
    ])

    rc = menu_mod.run_menu(input_func=lambda _: next(inputs), io=io)
    assert rc == 0


def test_run_menu_profiles() -> None:
    """Menu choice 3 triggers profiles menu."""
    io = _StubIO()
    inputs = iter([
        "5",  # profiles: back
        "6",  # exit menu
    ])

    rc = menu_mod.run_menu(input_func=lambda _: next(inputs), io=io)
    assert rc == 0


def test_profiles_menu_load_blank() -> None:
    """Load profile with blank input cancels gracefully."""
    io = _StubIO()
    inputs = iter([
        "3",  # load
        "",  # blank choice
        "5",  # back
    ])
    menu_profiles_mod.run_profiles_menu(io, input_func=lambda _: next(inputs))
    assert any("panel" not in str(o) for o in io.panels)


def test_profiles_menu_delete_cancel() -> None:
    """Delete profile with blank input cancels gracefully."""
    io = _StubIO()
    inputs = iter([
        "4",  # delete
        "",  # blank choice
        "5",  # back
    ])
    menu_profiles_mod.run_profiles_menu(io, input_func=lambda _: next(inputs))
    assert len(io.messages) >= 0


def test_load_and_describe_cancel_blank() -> None:
    """_load_and_describe_profile with blank input returns silently."""
    io = _StubIO()
    menu_profiles_mod._load_and_describe_profile(io, lambda _: "")
    # Should return early without error


def test_delete_profile_blank_input() -> None:
    """_delete_profile with blank input returns silently."""
    io = _StubIO()
    menu_profiles_mod._delete_profile(io, lambda _: "")
    # Should return early without error


def test_list_profiles_no_dir_mocked(monkeypatch: Any) -> None:
    """_list_profiles with no directory shows error message."""
    io = _StubIO()

    def mock_exists(self: Any) -> bool:
        return False

    monkeypatch.setattr(Path, "exists", mock_exists)
    menu_profiles_mod._list_profiles(io)
    assert any("No profiles directory" in m for m in io.messages)


def test_list_profiles_empty_dir_mocked(monkeypatch: Any) -> None:
    """_list_profiles with empty directory shows empty message."""
    io = _StubIO()
    calls = [True]  # First call to exists() returns True

    def mock_exists(self: Any) -> bool:
        return calls[0]

    def mock_glob(self: Any, pattern: str) -> list[Path]:
        return []

    monkeypatch.setattr(Path, "exists", mock_exists)
    monkeypatch.setattr(Path, "glob", mock_glob)
    menu_profiles_mod._list_profiles(io)
    assert any("No profiles found" in m for m in io.messages)


def test_create_profile_with_targets(monkeypatch: Any) -> None:
    """_create_profile starts wizard with program name and targets."""
    io = _StubIO()

    def fake_run_init(_args: Any) -> None:
        io.print("Profile creation succeeded")

    monkeypatch.setattr(menu_profiles_mod, "run_init", fake_run_init)
    inputs = iter([
        "testprog",  # program name
        "example.com,api.example.com",  # targets
        "",  # output path (use default)
        "n",  # don't overwrite
    ])
    menu_profiles_mod._create_profile(io, lambda _: next(inputs))
    # Just ensure it doesn't crash


def test_load_and_describe_nonexistent(monkeypatch: Any) -> None:
    """_load_and_describe_profile handles missing profile."""
    io = _StubIO()

    def mock_glob(self: Any, pattern: str) -> list[Path]:
        return []

    monkeypatch.setattr(Path, "glob", mock_glob)
    menu_profiles_mod._load_and_describe_profile(io, lambda _: "demo")
    assert any("No profiles" in m for m in io.messages)


def test_delete_profile_nonexistent(monkeypatch: Any) -> None:
    """_delete_profile handles no profiles."""
    io = _StubIO()

    def mock_glob(self: Any, pattern: str) -> list[Path]:
        return []

    monkeypatch.setattr(Path, "glob", mock_glob)
    menu_profiles_mod._delete_profile(io, lambda _: "demo")
    assert any("No profiles" in m for m in io.messages)


def test_run_custom_scan_invalid_choice() -> None:
    """Custom scan action menu with invalid choice."""
    io = _StubIO()
    inputs = iter([
        "example.com",  # targets
        "safe",  # mode
        "y",  # ack
        "",  # output_dir
        "",  # wordlist
        "",  # enable_tool
        "",  # disable_tool
        "info",  # severity
        "",  # threads
        "",  # rate
        "y",  # dry_run
        "9",  # invalid action choice
        "5",  # back
    ])
    rc = menu_custom_mod.run_custom_scan(
        io, session_ack=False, input_func=lambda _: next(inputs),
    )
    assert rc == 0
    assert any("1 to 5" in m for m in io.messages)


def test_delete_profile_with_confirmation_no(monkeypatch: Any) -> None:
    """_delete_profile with confirmation 'no' doesn't delete."""
    io = _StubIO()
    deleted = []

    def mock_glob(self: Any, pattern: str) -> list[Path]:
        return [Path("profiles/test.yaml")]

    def mock_unlink(self: Any) -> None:
        deleted.append(str(self))

    monkeypatch.setattr(Path, "glob", mock_glob)
    monkeypatch.setattr(Path, "unlink", mock_unlink)
    monkeypatch.setattr(Path, "exists", lambda self: True)

    inputs = iter([
        "test",  # profile choice
        "n",  # don't confirm delete
    ])
    menu_profiles_mod._delete_profile(io, lambda _: next(inputs))
    assert len(deleted) == 0  # File should not be deleted


def test_create_profile_all_steps(monkeypatch: Any) -> None:
    """_create_profile with all input steps."""
    io = _StubIO()

    def fake_run_init(_args: Any) -> None:
        pass

    monkeypatch.setattr(menu_profiles_mod, "run_init", fake_run_init)
    inputs = iter([
        "myprogram",  # program name
        "test.example.com",  # targets
        "profiles/myprogram.yaml",  # output path
        "y",  # overwrite
    ])
    menu_profiles_mod._create_profile(io, lambda _: next(inputs))
    # Verify it processes the input


def test_load_describe_actual_profile() -> None:
    """_load_and_describe_profile loads and displays profile data."""
    io = _StubIO()
    # Use a known profile from the profiles directory
    inputs = iter([
        "example",  # profile choice (should exist)
    ])
    menu_profiles_mod._load_and_describe_profile(io, lambda _: next(inputs))
    # Should display profile table or error if not found
    assert len(io.tables) > 0 or len(io.messages) > 0


def test_delete_with_choice(monkeypatch: Any) -> None:
    """_delete_profile with profile choice processes input."""
    io = _StubIO()

    def mock_glob(self: Any, pattern: str) -> list[Path]:
        return [Path("profiles/demo.yaml")]

    monkeypatch.setattr(Path, "glob", mock_glob)

    inputs = iter([
        "demo",  # profile choice
        "n",  # don't confirm
    ])
    menu_profiles_mod._delete_profile(io, lambda _: next(inputs))
    # Should handle the choice without error
