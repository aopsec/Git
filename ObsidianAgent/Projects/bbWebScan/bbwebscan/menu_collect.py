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
from bbwebscan.menu_types import InputFunc, ScanSettings, default_input


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


# [v0.5.9] Selection-based prompts for the form-style scan wizard
# (`menu_form.run_form_scan`). Kept stdlib-only — they reuse the same
# ``input_func`` indirection the rest of the menu uses so tests can drive
# them deterministically.
def prompt_select(
    label: str,
    options: list[str],
    default: int = 1,
    input_func: InputFunc = default_input,
) -> str:
    """Present a numbered list; return the selected option string.

    Empty input returns the default option (1-indexed). Invalid choices
    re-prompt until a valid 1..N integer is entered.
    """
    if not options:
        raise ValueError("prompt_select requires at least one option")
    if not 1 <= default <= len(options):
        raise ValueError(
            f"default must be in 1..{len(options)}, got {default}"
        )
    print(label)
    rendered = "  ".join(f"[{idx}] {opt}" for idx, opt in enumerate(options, 1))
    print(rendered)
    while True:
        raw = input_func(f"Enter choice [{default}]: ").strip()
        if not raw:
            return options[default - 1]
        try:
            picked = int(raw)
        except ValueError:
            print(f"Invalid choice: {raw!r}. Enter a number 1..{len(options)}.")
            continue
        if 1 <= picked <= len(options):
            return options[picked - 1]
        print(f"Out of range: {picked}. Enter a number 1..{len(options)}.")


def prompt_multiselect(
    label: str,
    options: list[str],
    default_all: bool = False,
    input_func: InputFunc = default_input,
) -> list[str]:
    """Present a numbered checkbox list; return list of selected option strings.

    Accepts comma-separated indices (``1,3,5``), ``a`` for all, ``n`` for none.
    Empty input returns the default selection (all when ``default_all`` is
    True, otherwise an empty list). Invalid input re-prompts.
    """
    if not options:
        return []
    print(label)
    for idx, opt in enumerate(options, 1):
        marker = "x" if default_all else " "
        print(f"  [{marker}] [{idx}] {opt}")
    while True:
        raw = input_func(
            "Enter numbers separated by commas (e.g. 1,3,5), 'a' for all, 'n' for none: "
        ).strip().lower()
        if not raw:
            return list(options) if default_all else []
        if raw == "a":
            return list(options)
        if raw == "n":
            return []
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        try:
            indices = [int(p) for p in parts]
        except ValueError:
            print(f"Invalid input: {raw!r}. Use comma-separated numbers, 'a', or 'n'.")
            continue
        if any(idx < 1 or idx > len(options) for idx in indices):
            print(f"Out of range. Valid indices: 1..{len(options)}.")
            continue
        # Preserve option order; de-duplicate while keeping first occurrence.
        seen: set[int] = set()
        ordered: list[str] = []
        for idx in indices:
            if idx not in seen:
                seen.add(idx)
                ordered.append(options[idx - 1])
        return ordered
