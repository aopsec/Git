from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from bbwebscan.models import RunConfig

InputFunc = Callable[[str], str]
ScanExecutor = Callable[[RunConfig], int]


class MenuIO(Protocol):
    def print(self, message: str = "") -> None: ...
    def panel(self, title: str, body: str) -> None: ...
    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None: ...


@dataclass
class ScanSettings:
    profile: str | None = None
    targets: list[str] = field(default_factory=list)
    input_file: str | None = None
    mode: Literal["safe", "aggressive"] = "safe"
    ack_authorized: bool = False
    headers: list[str] = field(default_factory=list)
    cookies: list[str] = field(default_factory=list)
    raw_request: str | None = None
    output_dir: str | None = None
    wordlist: str | None = None
    enable_tool: list[str] = field(default_factory=list)
    disable_tool: list[str] = field(default_factory=list)
    threads: int | None = None
    rate: int | None = None
    tool_timeout: int | None = None
    cmd_timeout: int | None = None
    max_attempts: int | None = None
    backoff_s: float | None = None
    severity: Literal["info", "low", "medium", "high", "critical"] = "info"
    check_dns: bool = False
    enumerate_subdomains: bool = False
    amass_mode: Literal["passive", "active", "intel"] = "passive"
    api_discovery: bool = False
    dry_run: bool = True
    quiet: bool = False
    strict_identity: bool = False
    profile_auth_headers: dict[str, str] = field(default_factory=dict)
    profile_auth_cookies: dict[str, str] = field(default_factory=dict)


def default_input(prompt: str) -> str:
    return input(prompt)
