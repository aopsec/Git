from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# [v0.4.3 Item 5] Severity ladder used to gate findings via --severity.
SEVERITY_ORDER: tuple[str, ...] = ("info", "low", "medium", "high", "critical")


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headers: dict[str, str] = Field(default_factory=dict)
    cookies: dict[str, str] = Field(default_factory=dict)
    raw_request: Path | None = None

    def cookie_header(self) -> str | None:
        if not self.cookies:
            return None
        return "; ".join(f"{key}={value}" for key, value in sorted(self.cookies.items()))


class RetryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_attempts: int = 1
    backoff_s: float = 2.0
    transient_exit_codes: tuple[int, ...] = (124, 137, 143)

    @field_validator("max_attempts")
    @classmethod
    def _attempts_at_least_one(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_attempts must be >= 1")
        return value


class ProgramProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_name: str = "ad-hoc"
    seed_urls: list[str] = Field(default_factory=list)
    allowed_hosts: list[str] = Field(default_factory=list)
    denied_hosts: list[str] = Field(default_factory=list)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    mode_default: str = "safe"
    enabled_tools: list[str] = Field(default_factory=list)
    wordlist: Path = Path("/usr/share/dirb/wordlists/common.txt")
    threads: int = 10
    rate: int = 25
    tool_timeout_s: int = 15
    command_wall_clock_s: int = 900
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    tool_identity: dict[str, str] = Field(default_factory=dict)
    discovery_status_filter: list[str] = Field(
        default_factory=lambda: ["200", "301", "302", "307", "308"]
    )
    nuclei_max_targets: int = 1000


class RunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_name: str
    seed_urls: list[str]
    allowed_hosts: list[str]
    denied_hosts: list[str]
    auth: AuthConfig
    mode: str
    enabled_tools: list[str]
    wordlist: Path
    threads: int
    rate: int
    tool_timeout_s: int
    command_wall_clock_s: int
    retry: RetryPolicy
    output_dir: Path
    target_inputs: list[str]
    input_file: Path | None = None
    check_tools: bool = False
    dry_run: bool = False
    ack_authorized: bool = False
    verbose: bool = True
    strict_identity: bool = False
    profile_tool_identity: dict[str, str] = Field(default_factory=dict)
    min_severity: str = "info"
    preflight_dns: bool = False
    enumerate_subdomains: bool = False
    api_discovery: bool = False
    amass_mode: Literal["passive", "active", "intel"] = "passive"
    scrapy_deep: bool = False
    scrapy_max_depth: int = Field(default=2, ge=1, le=5)
    scrapy_js_render: bool = False
    discovery_status_filter: list[str] = Field(
        default_factory=lambda: ["200", "301", "302", "307", "308"]
    )
    jwt_analysis: bool = False
    sqlmap_mode: Literal["off", "smooth", "aggressive"] = "off"
    sqlmap_timeout: int = 600
    nuclei_max_targets: int = 1000


class NormalizedTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str
    host: str
    seed_url: str


class ToolStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    required: bool
    found: bool
    path: Path | None = None
    version: str | None = None
    note: str | None = None
    identity: Literal["verified", "suspect"] | None = None
    path_gap: Path | None = None
    shadowed_by: Path | None = None


class ScopeDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    allowed: bool
    reason: str


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    kind: str
    target: str
    severity: str
    title: str
    evidence: str


class CommandPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    label: str
    command: list[str]
    artifacts: list[Path] = Field(default_factory=list)
    # [v0.5.5 sec-fix] argv positions whose VALUES carry a secret. The runner
    # masks these before any dry-run echo or log write, complementing the
    # header-flag redaction in ``runner.redact_command_for_log``. Used by the
    # jwt_tool stage today; future stages that pass secrets via non-header
    # argv slots (e.g. ``sqlmap --auth-cred user:pass``) opt in by setting it.
    redact_indices: list[int] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    label: str
    command: list[str]
    status: str
    exit_code: int | None = None
    stdout_log: Path | None = None
    stderr_log: Path | None = None
    artifacts: list[Path] = Field(default_factory=list)
    attempts: int = 1
    error: str | None = None


class RunArtifacts(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: Path
    logs: Path
    artifacts: Path


class RunSummary(BaseModel):
    """[v0.4.3 Item 3] Compact summary of a past run dir for `bbwebscan history`."""
    model_config = ConfigDict(extra="forbid")

    run_dir: Path
    program_name: str
    mode: str
    finding_count: int
    allowed_decisions: int
    rejected_decisions: int
    timestamp: str
