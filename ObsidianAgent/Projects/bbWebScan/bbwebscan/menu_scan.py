from __future__ import annotations

from typing import Literal, cast

from bbwebscan.config import build_run_config
from bbwebscan.menu_command import build_scan_command, scan_settings_to_args
from bbwebscan.menu_profile import save_profile_interactive
from bbwebscan.menu_prompts import (
    blank_to_none,
    choice,
    collect_repeatable,
    prompt,
    prompt_bool,
    prompt_float,
    prompt_int,
    split_csv,
    validate_tools,
)
from bbwebscan.menu_types import InputFunc, MenuIO, ScanExecutor, ScanSettings, default_input
from bbwebscan.pipeline import execute_scan


def collect_scan_settings(
    existing: ScanSettings | None = None,
    *,
    input_func: InputFunc = default_input,
) -> ScanSettings:
    """[MENU-051] Collect scan args interactively, then reuse build_run_config."""
    base = existing or ScanSettings()
    profile = blank_to_none(prompt("Profile YAML path", base.profile, input_func))
    targets = split_csv(prompt("Targets (comma-separated)", ",".join(base.targets), input_func))
    input_file = blank_to_none(prompt("Input file", base.input_file, input_func))
    mode = _collect_mode(base, input_func)
    ack = _collect_authorization_ack(mode, base.ack_authorized, input_func)
    enable_tool = validate_tools(split_csv(prompt(
        "Enable extra tools", ",".join(base.enable_tool), input_func,
    )))
    disable_tool = validate_tools(split_csv(prompt(
        "Disable tools", ",".join(base.disable_tool), input_func,
    )))
    enumerate_subdomains = prompt_bool(
        "Enumerate subdomains with amass", base.enumerate_subdomains, input_func,
    )
    amass_mode, ack = _collect_amass_mode(base, enumerate_subdomains, ack, input_func)
    sqlmap_mode, ack = _collect_sqlmap_mode(base, ack, input_func)
    port_scan = prompt_bool("Port-scan with naabu", base.port_scan, input_func)
    port_scan_mode, ack = _collect_port_scan_mode(base, port_scan, ack, input_func)
    port_scan_rate = _collect_port_scan_rate(base, port_scan, input_func)
    return ScanSettings(
        profile=profile,
        targets=targets,
        input_file=input_file,
        mode=mode,
        ack_authorized=ack,
        headers=collect_repeatable("one-off header (Name: value)", base.headers, input_func),
        cookies=collect_repeatable("one-off cookie (name=value)", base.cookies, input_func),
        raw_request=blank_to_none(prompt("Raw request file", base.raw_request, input_func)),
        output_dir=blank_to_none(prompt("Output directory", base.output_dir, input_func)),
        wordlist=blank_to_none(prompt("Wordlist", base.wordlist, input_func)),
        enable_tool=enable_tool,
        disable_tool=disable_tool,
        threads=prompt_int("Threads", base.threads, input_func),
        rate=prompt_int("Rate", base.rate, input_func),
        tool_timeout=prompt_int("Per-tool timeout seconds", base.tool_timeout, input_func),
        cmd_timeout=prompt_int("Command timeout seconds", base.cmd_timeout, input_func),
        max_attempts=prompt_int("Retry max attempts", base.max_attempts, input_func),
        backoff_s=prompt_float("Retry backoff seconds", base.backoff_s, input_func),
        severity=_collect_severity(base, input_func),
        check_dns=prompt_bool("Check DNS before scan", base.check_dns, input_func),
        enumerate_subdomains=enumerate_subdomains,
        amass_mode=amass_mode,
        api_discovery=prompt_bool(
            "Run API discovery with kiterunner", base.api_discovery, input_func,
        ),
        scrapy_deep=prompt_bool(
            "Scrapy deep mode (extract secrets/credentials)", base.scrapy_deep, input_func,
        ),
        scrapy_max_depth=_collect_scrapy_depth(base, input_func),
        scrapy_js_render=prompt_bool(
            "Scrapy JS rendering via scrapy-playwright (requires [js] extra)",
            base.scrapy_js_render, input_func,
        ),
        jwt_analysis=prompt_bool(
            "Run jwt_tool against Bearer tokens in Authorization header",
            base.jwt_analysis, input_func,
        ),
        sqlmap_mode=sqlmap_mode,
        sqlmap_timeout=_collect_sqlmap_timeout(base, input_func),
        port_scan=port_scan,
        port_scan_mode=port_scan_mode,
        port_scan_rate=port_scan_rate,
        dry_run=prompt_bool("Default to dry-run", base.dry_run, input_func),
        quiet=prompt_bool("Quiet progress output", base.quiet, input_func),
        strict_identity=prompt_bool("Strict tool identity", base.strict_identity, input_func),
        profile_auth_headers=dict(base.profile_auth_headers),
        profile_auth_cookies=dict(base.profile_auth_cookies),
    )


def run_scan_action_menu(
    settings: ScanSettings,
    io: MenuIO,
    *,
    input_func: InputFunc = default_input,
    scan_executor: ScanExecutor = execute_scan,
) -> int:
    current = settings
    while True:
        io.panel("Scan Action Menu", _action_menu_body())
        choice_value = input_func("Choose [1-6]: ").strip()
        if choice_value == "1":
            io.print(build_scan_command(current, dry_run_override=current.dry_run))
        elif choice_value == "2":
            return _run_configured_scan(current, True, io, scan_executor)
        elif choice_value == "3":
            return _run_configured_scan(current, False, io, scan_executor)
        elif choice_value == "4":
            try:
                path = save_profile_interactive(current, io, input_func=input_func)
            except (FileExistsError, ValueError) as exc:
                io.print(f"[bbwebscan menu] {exc}")
                return 2
            io.print(f"wrote {path}")
        elif choice_value == "5":
            current = collect_scan_settings(current, input_func=input_func)
        elif choice_value == "6":
            return 0
        else:
            io.print("Choose a number from 1 to 6.")


def _run_configured_scan(
    settings: ScanSettings,
    dry_run: bool,
    io: MenuIO,
    scan_executor: ScanExecutor,
) -> int:
    try:
        config = build_run_config(scan_settings_to_args(settings, dry_run_override=dry_run))
        return scan_executor(config)
    except (FileNotFoundError, ValueError) as exc:
        io.print(f"[bbwebscan menu] {exc}")
        return 2


def _collect_mode(
    base: ScanSettings,
    input_func: InputFunc,
) -> Literal["safe", "aggressive"]:
    return cast(
        Literal["safe", "aggressive"],
        choice("Mode", ("safe", "aggressive"), base.mode, input_func),
    )


def _collect_severity(
    base: ScanSettings,
    input_func: InputFunc,
) -> Literal["info", "low", "medium", "high", "critical"]:
    return cast(
        Literal["info", "low", "medium", "high", "critical"],
        choice(
            "Minimum severity",
            ("info", "low", "medium", "high", "critical"),
            base.severity,
            input_func,
        ),
    )


def _collect_authorization_ack(
    mode: Literal["safe", "aggressive"],
    existing_ack: bool,
    input_func: InputFunc,
) -> bool:
    if mode == "safe":
        return prompt_bool("Authorization acknowledgement", existing_ack, input_func)
    response = input_func("Type AUTHORIZED to acknowledge aggressive authorization: ").strip()
    return response == "AUTHORIZED"


def _collect_scrapy_depth(
    base: ScanSettings,
    input_func: InputFunc,
) -> int:
    depth = prompt_int("Scrapy max crawl depth (1-5)", base.scrapy_max_depth, input_func)
    if depth is None:
        return base.scrapy_max_depth
    return max(1, min(5, depth))


def _collect_amass_mode(
    base: ScanSettings,
    enumerate_subdomains: bool,
    ack: bool,
    input_func: InputFunc,
) -> tuple[Literal["passive", "active", "intel"], bool]:
    if not enumerate_subdomains:
        return (base.amass_mode, ack)
    mode = cast(
        Literal["passive", "active", "intel"],
        choice("Amass mode", ("passive", "active", "intel"), base.amass_mode, input_func),
    )
    if mode != "passive" and not ack:
        ack = _collect_authorization_ack("aggressive", False, input_func)
    return (mode, ack)


def _collect_sqlmap_mode(
    base: ScanSettings,
    ack: bool,
    input_func: InputFunc,
) -> tuple[Literal["off", "smooth", "aggressive"], bool]:
    mode = cast(
        Literal["off", "smooth", "aggressive"],
        choice("sqlmap mode", ("off", "smooth", "aggressive"), base.sqlmap_mode, input_func),
    )
    if mode == "aggressive" and not ack:
        ack = _collect_authorization_ack("aggressive", False, input_func)
    return (mode, ack)


def _collect_sqlmap_timeout(
    base: ScanSettings,
    input_func: InputFunc,
) -> int:
    timeout = prompt_int("sqlmap per-URL timeout seconds", base.sqlmap_timeout, input_func)
    if timeout is None or timeout < 1:
        return base.sqlmap_timeout
    return timeout


def _collect_port_scan_mode(
    base: ScanSettings,
    port_scan: bool,
    ack: bool,
    input_func: InputFunc,
) -> tuple[Literal["top-100", "top-1000", "full"], bool]:
    if not port_scan:
        return (base.port_scan_mode, ack)
    mode = cast(
        Literal["top-100", "top-1000", "full"],
        choice(
            "naabu mode", ("top-100", "top-1000", "full"), base.port_scan_mode, input_func,
        ),
    )
    if mode == "full" and not ack:
        ack = _collect_authorization_ack("aggressive", False, input_func)
    return (mode, ack)


def _collect_port_scan_rate(
    base: ScanSettings,
    port_scan: bool,
    input_func: InputFunc,
) -> int:
    if not port_scan:
        return base.port_scan_rate
    rate = prompt_int("naabu rate (packets/sec)", base.port_scan_rate, input_func)
    if rate is None or rate < 1:
        return base.port_scan_rate
    return rate


def _action_menu_body() -> str:
    return "\n".join((
        "1. Preview equivalent command",
        "2. Dry-run",
        "3. Run scan",
        "4. Save profile",
        "5. Edit settings",
        "6. Back to main menu",
    ))
