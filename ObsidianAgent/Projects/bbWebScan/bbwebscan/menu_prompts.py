from __future__ import annotations

from collections.abc import Callable

from bbwebscan.config import SUPPORTED_TOOLS
from bbwebscan.menu_types import InputFunc


def prompt(label: str, default: str | None, input_func: InputFunc) -> str:
    suffix = f" [{default}]" if default not in (None, "") else ""
    value = input_func(f"{label}{suffix}: ").strip()
    return value if value else (default or "")


def choice(
    label: str,
    choices: tuple[str, ...],
    default: str,
    input_func: InputFunc,
) -> str:
    while True:
        value = prompt(f"{label} ({'/'.join(choices)})", default, input_func)
        if value in choices:
            return value
        print(f"Choose one of: {', '.join(choices)}")


def prompt_bool(label: str, default: bool, input_func: InputFunc) -> bool:
    default_text = "y" if default else "n"
    while True:
        value = prompt(f"{label} [y/n]", default_text, input_func).lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Choose y or n.")


def prompt_int(label: str, default: int | None, input_func: InputFunc) -> int | None:
    value = prompt(label, str_or_none(default), input_func)
    if not value:
        return None
    return int(value)


def prompt_float(
    label: str,
    default: float | None,
    input_func: InputFunc,
) -> float | None:
    value = prompt(label, str_or_none(default), input_func)
    if not value:
        return None
    return float(value)


def collect_repeatable(label: str, existing: list[str], input_func: InputFunc) -> list[str]:
    values = list(existing)
    while prompt_bool(f"Add {label}", False, input_func):
        values.append(prompt(label, None, input_func))
    return values


def collect_env_refs(label: str, input_func: InputFunc) -> dict[str, str]:
    values: dict[str, str] = {}
    while prompt_bool(f"Add {label} env reference", False, input_func):
        name = prompt(f"{label} name", None, input_func)
        value = prompt(f"{label} value", None, input_func)
        values[name] = value
    return values


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def blank_to_none(value: str) -> str | None:
    return value or None


def validate_tools(tools: list[str]) -> list[str]:
    unsupported = sorted(set(tools) - set(SUPPORTED_TOOLS))
    if unsupported:
        raise ValueError(f"Unsupported tools selected: {', '.join(unsupported)}")
    return tools


def str_or_none(value: int | float | None) -> str | None:
    return None if value is None else str(value)


def confirm(label: str, input_func: InputFunc, *, default: bool = False) -> bool:
    default_text = "y" if default else "n"
    value = input_func(f"{label}? [y/n] [{default_text}]: ").strip().lower()
    if not value:
        value = default_text
    return value in {"y", "yes"}


def append_optional(args: list[str], flag: str, value: str | None) -> None:
    if value:
        args.extend([flag, value])


def append_repeatable(
    args: list[str],
    flag: str,
    values: list[str],
    redact_auth: bool,
    redactor: Callable[[str], str],
) -> None:
    for value in values:
        args.extend([flag, redactor(value) if redact_auth else value])
