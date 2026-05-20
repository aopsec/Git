"""Form-select scan wizard for bbWebScan.

[v0.5.9] Provides a selection-based alternative to ``menu_custom``'s
free-text prompts. Every discrete option (scan mode, sqlmap mode,
scrapy-extended, wordlist, profile) is rendered as a numbered list so the
operator picks from presented choices rather than typing values verbatim.

Entry point: :func:`run_form_scan`. Returns a populated :class:`RunConfig`
or ``None`` when the operator cancels (no target supplied).
"""
from __future__ import annotations

from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from bbwebscan.config import OPTIONAL_TOOLS, build_run_config, load_profile
from bbwebscan.menu_collect import (
    collect_authorization_ack,
    prompt_multiselect,
    prompt_select,
)
from bbwebscan.menu_types import InputFunc, default_input
from bbwebscan.models import RunConfig

_PROFILES_DIR = Path("profiles")
_WORDLIST_PRESETS: tuple[str, ...] = (
    "/usr/share/dirb/wordlists/common.txt",
    "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
)
_CUSTOM_WORDLIST_LABEL = "Custom"
_NO_PROFILE_LABEL = "None"


def run_form_scan(
    config: RunConfig | None = None,
    *,
    input_func: InputFunc = default_input,
) -> RunConfig | None:
    """Form-based scan wizard using selection prompts.

    Returns a fully-built :class:`RunConfig` or ``None`` when the operator
    supplies an empty target (treated as cancellation). The ``config``
    parameter is accepted for forward compatibility (pre-populating
    settings from an existing run) but not yet consumed.
    """
    del config  # Reserved for future pre-population; not used in v0.5.9.

    target = input_func("Target URL: ").strip()
    if not target:
        return None

    profile_choice = _select_profile(input_func)
    profile_path: str | None = None
    profile_tools: list[str] = []
    if profile_choice != _NO_PROFILE_LABEL:
        profile_path = str(_PROFILES_DIR / f"{profile_choice}.yaml")
        try:
            loaded = load_profile(profile_path)
            profile_tools = list(loaded.enabled_tools)
        except (FileNotFoundError, ValueError):
            profile_path = None
            profile_tools = []

    mode = cast(
        Literal["safe", "aggressive"],
        prompt_select(
            "Scan mode", ["safe", "aggressive"], default=1, input_func=input_func,
        ),
    )

    tools = _select_tools(profile_tools, input_func)
    sqlmap_mode = cast(
        Literal["off", "smooth", "aggressive"],
        prompt_select(
            "sqlmap mode",
            ["off", "smooth", "aggressive"],
            default=1,
            input_func=input_func,
        ),
    )
    scrapy_extended_choice = prompt_select(
        "Scrapy extended harvesting",
        ["no", "yes"],
        default=1,
        input_func=input_func,
    )
    scrapy_extended = scrapy_extended_choice == "yes"

    wordlist = _select_wordlist(input_func)

    # Aggressive sqlmap mirrors menu_custom: must re-prompt for authorization
    # (mode-derived ack is mandatory even when scan-mode itself stays "safe",
    # because aggressive sqlmap drives high target load regardless).
    ack_authorized = mode == "aggressive"
    if mode == "aggressive":
        ack_authorized = collect_authorization_ack(mode, False, input_func)
    if sqlmap_mode == "aggressive":
        ack_authorized = collect_authorization_ack("aggressive", ack_authorized, input_func)

    namespace = _build_namespace(
        target=target,
        profile_path=profile_path,
        mode=mode,
        ack_authorized=ack_authorized,
        tools=tools,
        sqlmap_mode=sqlmap_mode,
        scrapy_extended=scrapy_extended,
        wordlist=wordlist,
    )
    return build_run_config(namespace)


def _select_profile(input_func: InputFunc) -> str:
    """Return the selected profile name (stem) or ``_NO_PROFILE_LABEL``."""
    available = _list_profile_names()
    options = [*available, _NO_PROFILE_LABEL]
    return prompt_select(
        "Load a saved profile",
        options,
        default=len(options),  # default to "None"
        input_func=input_func,
    )


def _list_profile_names() -> list[str]:
    if not _PROFILES_DIR.is_dir():
        return []
    return sorted(p.stem for p in _PROFILES_DIR.glob("*.yaml"))


def _select_tools(profile_tools: list[str], input_func: InputFunc) -> list[str]:
    options = list(OPTIONAL_TOOLS)
    selected = prompt_multiselect(
        "Enable tools",
        options,
        default_all=False,
        input_func=input_func,
    )
    # Pre-select tools from profile when present and operator did not pick any
    # — preserves the profile's intent without overriding explicit choices.
    if not selected and profile_tools:
        return [tool for tool in profile_tools if tool in options]
    return selected


def _select_wordlist(input_func: InputFunc) -> str:
    options = [*_WORDLIST_PRESETS, _CUSTOM_WORDLIST_LABEL]
    choice = prompt_select("Wordlist", options, default=1, input_func=input_func)
    if choice == _CUSTOM_WORDLIST_LABEL:
        return input_func("Wordlist path: ").strip()
    return choice


def _build_namespace(  # noqa: PLR0913 - flag-to-Namespace mapping is naturally wide
    *,
    target: str,
    profile_path: str | None,
    mode: Literal["safe", "aggressive"],
    ack_authorized: bool,
    tools: list[str],
    sqlmap_mode: Literal["off", "smooth", "aggressive"],
    scrapy_extended: bool,
    wordlist: str,
) -> Namespace:
    """Translate wizard answers into the Namespace ``build_run_config`` expects."""
    run_label = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Namespace(
        profile=profile_path,
        target=[target],
        input=None,
        mode=mode,
        ack_authorized=ack_authorized,
        header=[],
        cookie=[],
        raw_request=None,
        output_dir=None,
        wordlist=wordlist or None,
        check_tools=False,
        dry_run=False,
        enable_tool=list(tools),
        disable_tool=[],
        threads=None,
        rate=None,
        tool_timeout=None,
        cmd_timeout=None,
        max_attempts=None,
        backoff_s=None,
        quiet=False,
        strict_identity=False,
        severity="info",
        check_dns=False,
        enumerate_subdomains=False,
        amass_mode="passive",
        api_discovery=False,
        scrapy_deep=False,
        scrapy_max_depth=2,
        scrapy_js_render=False,
        scrapy_extended=scrapy_extended,
        jwt_analysis=False,
        sqlmap_mode=sqlmap_mode,
        sqlmap_timeout=600,
        port_scan=False,
        port_scan_mode="top-100",
        port_scan_rate=1000,
        run_label=run_label,
    )
