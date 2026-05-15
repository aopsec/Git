from __future__ import annotations

import argparse
import shlex
from datetime import UTC, datetime

from bbwebscan.menu_prompts import append_optional, append_repeatable, str_or_none
from bbwebscan.menu_types import ScanSettings

_DEFAULT_SCRAPY_MAX_DEPTH: int = 2
_DEFAULT_SQLMAP_TIMEOUT: int = 600


def scan_settings_to_args(
    settings: ScanSettings,
    *,
    dry_run_override: bool | None = None,
    run_label: str | None = None,
) -> argparse.Namespace:
    label = run_label or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return argparse.Namespace(
        profile=settings.profile,
        target=list(settings.targets),
        input=settings.input_file,
        mode=settings.mode,
        ack_authorized=settings.ack_authorized,
        header=list(settings.headers),
        cookie=list(settings.cookies),
        raw_request=settings.raw_request,
        output_dir=settings.output_dir,
        wordlist=settings.wordlist,
        check_tools=False,
        dry_run=settings.dry_run if dry_run_override is None else dry_run_override,
        enable_tool=list(settings.enable_tool),
        disable_tool=list(settings.disable_tool),
        threads=settings.threads,
        rate=settings.rate,
        tool_timeout=settings.tool_timeout,
        cmd_timeout=settings.cmd_timeout,
        max_attempts=settings.max_attempts,
        backoff_s=settings.backoff_s,
        quiet=settings.quiet,
        strict_identity=settings.strict_identity,
        severity=settings.severity,
        check_dns=settings.check_dns,
        enumerate_subdomains=settings.enumerate_subdomains,
        amass_mode=settings.amass_mode,
        api_discovery=settings.api_discovery,
        scrapy_deep=settings.scrapy_deep,
        scrapy_max_depth=settings.scrapy_max_depth,
        scrapy_js_render=settings.scrapy_js_render,
        jwt_analysis=settings.jwt_analysis,
        sqlmap_mode=settings.sqlmap_mode,
        sqlmap_timeout=settings.sqlmap_timeout,
        run_label=label,
    )


def build_scan_command(
    settings: ScanSettings,
    *,
    dry_run_override: bool | None = None,
    redact_auth: bool = True,
) -> str:
    args = scan_command_args(settings, dry_run_override=dry_run_override, redact_auth=redact_auth)
    return shlex.join(args)


def scan_command_args(  # noqa: PLR0912 - flag-to-argv mapping is naturally wide
    settings: ScanSettings,
    *,
    dry_run_override: bool | None,
    redact_auth: bool,
) -> list[str]:
    args = ["bbwebscan", "scan"]
    append_optional(args, "--profile", settings.profile)
    for target in settings.targets:
        args.extend(["--target", target])
    append_optional(args, "--input", settings.input_file)
    append_optional(args, "--mode", settings.mode)
    if settings.ack_authorized:
        args.append("--ack-authorized")
    append_repeatable(args, "--header", settings.headers, redact_auth, redact_header)
    append_repeatable(args, "--cookie", settings.cookies, redact_auth, redact_cookie)
    append_optional(args, "--raw-request", settings.raw_request)
    append_optional(args, "--output-dir", settings.output_dir)
    append_optional(args, "--wordlist", settings.wordlist)
    _append_tools(args, settings)
    _append_tuning(args, settings)
    if settings.severity != "info":
        args.extend(["--severity", settings.severity])
    if settings.check_dns:
        args.append("--check-dns")
    if settings.enumerate_subdomains:
        args.append("--enumerate-subdomains")
    if settings.amass_mode != "passive":
        args.extend(["--amass-mode", settings.amass_mode])
    if settings.api_discovery:
        args.append("--api-discovery")
    if settings.scrapy_deep:
        args.append("--scrapy-deep")
    if settings.scrapy_max_depth != _DEFAULT_SCRAPY_MAX_DEPTH:
        args.extend(["--scrapy-max-depth", str(settings.scrapy_max_depth)])
    if settings.scrapy_js_render:
        args.append("--scrapy-js-render")
    if settings.jwt_analysis:
        args.append("--jwt-analysis")
    if settings.sqlmap_mode != "off":
        args.extend(["--sqlmap-mode", settings.sqlmap_mode])
    if settings.sqlmap_timeout != _DEFAULT_SQLMAP_TIMEOUT:
        args.extend(["--sqlmap-timeout", str(settings.sqlmap_timeout)])
    if settings.dry_run if dry_run_override is None else dry_run_override:
        args.append("--dry-run")
    if settings.quiet:
        args.append("--quiet")
    if settings.strict_identity:
        args.append("--strict-identity")
    return args


def redact_header(value: str) -> str:
    if ":" not in value:
        return value
    key, _secret = value.split(":", 1)
    return f"{key}: <redacted>"


def redact_cookie(value: str) -> str:
    if "=" not in value:
        return value
    key, _secret = value.split("=", 1)
    return f"{key}=<redacted>"


def _append_tools(args: list[str], settings: ScanSettings) -> None:
    for tool in settings.enable_tool:
        args.extend(["--enable-tool", tool])
    for tool in settings.disable_tool:
        args.extend(["--disable-tool", tool])


def _append_tuning(args: list[str], settings: ScanSettings) -> None:
    append_optional(args, "--threads", str_or_none(settings.threads))
    append_optional(args, "--rate", str_or_none(settings.rate))
    append_optional(args, "--tool-timeout", str_or_none(settings.tool_timeout))
    append_optional(args, "--cmd-timeout", str_or_none(settings.cmd_timeout))
    append_optional(args, "--max-attempts", str_or_none(settings.max_attempts))
    append_optional(args, "--backoff-s", str_or_none(settings.backoff_s))
