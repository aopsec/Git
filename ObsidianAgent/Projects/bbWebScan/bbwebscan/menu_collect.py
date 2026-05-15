from __future__ import annotations

from typing import Literal, cast

from bbwebscan.menu_prompts import (
    blank_to_none,
    choice,
    prompt,
    prompt_bool,
    prompt_int,
    split_csv,
    validate_tools,
)
from bbwebscan.menu_types import InputFunc, ScanSettings


def collect_targets(settings: ScanSettings, input_func: InputFunc) -> list[str]:
    """Collect target hosts/domains via comma-separated prompt."""
    targets = split_csv(prompt("Targets (comma-separated)", ",".join(settings.targets), input_func))
    return targets if targets else settings.targets


def collect_mode(settings: ScanSettings, input_func: InputFunc) -> Literal["safe", "aggressive"]:
    """Collect scan mode: safe or aggressive."""
    return cast(
        Literal["safe", "aggressive"],
        choice("Scan mode", ("safe", "aggressive"), settings.mode, input_func),
    )


def collect_dry_run(settings: ScanSettings, input_func: InputFunc) -> bool:
    """Collect whether to default to dry-run."""
    return prompt_bool("Default to dry-run", settings.dry_run, input_func)


def collect_output_dir(settings: ScanSettings, input_func: InputFunc) -> str | None:
    """Collect output directory (optional)."""
    return blank_to_none(prompt("Output directory", settings.output_dir or "", input_func))


def collect_wordlist(settings: ScanSettings, input_func: InputFunc) -> str | None:
    """Collect wordlist path (auto-suggested by tech-stack if not set)."""
    label = "Wordlist path (blank=auto-suggest)"
    return blank_to_none(prompt(label, settings.wordlist or "", input_func))


def collect_disable_tools(settings: ScanSettings, input_func: InputFunc) -> list[str]:
    """Collect tools to disable. All tools are enabled by default via mode selection."""
    disable_raw = split_csv(
        prompt("Disable tools (blank=none)", ",".join(settings.disable_tool), input_func)
    )
    try:
        return validate_tools(disable_raw)
    except ValueError:
        return settings.disable_tool


def collect_severity(
    settings: ScanSettings,
    input_func: InputFunc,
) -> Literal["info", "low", "medium", "high", "critical"]:
    """Collect minimum severity threshold."""
    return cast(
        Literal["info", "low", "medium", "high", "critical"],
        choice(
            "Minimum severity",
            ("info", "low", "medium", "high", "critical"),
            settings.severity,
            input_func,
        ),
    )


def collect_threads(settings: ScanSettings, input_func: InputFunc) -> int | None:
    """Collect thread count (optional)."""
    threads = prompt_int("Threads", settings.threads, input_func)
    return threads if threads is not None else settings.threads


def collect_rate(settings: ScanSettings, input_func: InputFunc) -> int | None:
    """Collect request rate (optional)."""
    rate = prompt_int("Rate (requests/sec)", settings.rate, input_func)
    return rate if rate is not None else settings.rate


def collect_authorization_ack(
    mode: Literal["safe", "aggressive"],
    existing: bool,
    input_func: InputFunc,
) -> bool:
    """Collect authorization acknowledgement based on mode.

    Safe mode: yes/no prompt.
    Aggressive mode: must type 'AUTHORIZED'.
    """
    if mode == "safe":
        return prompt_bool("Authorization acknowledgement", existing, input_func)
    response = input_func("Type AUTHORIZED to acknowledge aggressive authorization: ").strip()
    return response == "AUTHORIZED"
