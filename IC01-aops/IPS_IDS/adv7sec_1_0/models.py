"""Pydantic models for ADV7Sec 1.0."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low"]
OutputMode = Literal["text", "json"]
SupportTier = Literal["native", "adapted", "experimental"]
MonitorStatus = Literal["ok", "warn", "missing"]
ActionName = Literal["stop-service", "disable-service", "kill-pid", "quarantine-path"]
EventSeverity = Literal["info", "low", "medium", "high", "critical"]


class Finding(BaseModel):
    """Audit finding for the current repository or runtime."""

    id: str = Field(min_length=1)
    severity: Severity
    title: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class RuntimeTarget(BaseModel):
    """Detected Linux target details."""

    distro_id: str = Field(min_length=1)
    distro_name: str = Field(min_length=1)
    package_manager: str = Field(min_length=1)
    init_system: str = Field(min_length=1)
    support_tier: SupportTier
    kernel_release: str = Field(min_length=1)


class Capability(BaseModel):
    """Runtime capability probe."""

    name: str = Field(min_length=1)
    available: bool
    detail: str = Field(min_length=1)


class PackageAction(BaseModel):
    """[FIX-LINUX-ADAPTERS] Package installation plan for one feature."""

    feature: str = Field(min_length=1)
    packages: list[str] = Field(default_factory=list)
    command: list[str] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)
    status: str = Field(min_length=1)


class ServiceBinding(BaseModel):
    """[FIX-LINUX-ADAPTERS] Service binding for one runtime feature."""

    feature: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    enable_command: list[str] = Field(default_factory=list)


class BackendPlan(BaseModel):
    """[FIX-LINUX-ADAPTERS] Cross-distro package and service backend plan."""

    package_manager: str = Field(min_length=1)
    service_manager: str = Field(min_length=1)
    package_actions: list[PackageAction] = Field(default_factory=list)
    service_bindings: list[ServiceBinding] = Field(default_factory=list)


class InstallOperation(BaseModel):
    """[FIX-UNIFIED-INSTALL] Planned or applied install operation."""

    kind: str = Field(min_length=1)
    feature: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    command: list[str] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)
    path: str | None = None


class OperationResult(BaseModel):
    """[FIX-BLOCKING-VALIDATION] Result of one executable install operation."""

    kind: str = Field(min_length=1)
    feature: str = Field(min_length=1)
    command: list[str] = Field(default_factory=list)
    status: Literal["ok", "failed", "skipped"]
    returncode: int | None = None
    detail: str = Field(min_length=1)


class InstallReport(BaseModel):
    """[FIX-UNIFIED-INSTALL] Install/apply report for the unified core."""

    root_dir: str = Field(min_length=1)
    execute: bool = False
    confirm: bool = False
    features: list[str] = Field(default_factory=list)
    operations: list[InstallOperation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    results: list[OperationResult] = Field(default_factory=list)
    exit_code: int = Field(default=0, ge=0)


class BuildStep(BaseModel):
    """Planned delivery step."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)


class BuildPlan(BaseModel):
    """High-level build plan for ADV7Sec 1.0."""

    version: str = Field(min_length=1)
    target: RuntimeTarget
    goals: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    runtime_layout: list[str] = Field(default_factory=list)
    cleanup_after_parity: list[str] = Field(default_factory=list)
    steps: list[BuildStep] = Field(default_factory=list)


class MonitorRecord(BaseModel):
    """Live source snapshot record."""

    source: str = Field(min_length=1)
    status: MonitorStatus
    summary: str = Field(min_length=1)


class ThreatEvent(BaseModel):
    """[FIX-LIVE-PIPELINE] Normalized runtime event from journald or local logs."""

    source: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    severity: EventSeverity
    summary: str = Field(min_length=1)
    raw: str = Field(min_length=1)
    rule: str | None = None
    pid: int | None = None
    path: str | None = None


class AutoResponseDecision(BaseModel):
    """[FIX-LIVE-PIPELINE] Safe automatic response derived from an event."""

    event_source: str = Field(min_length=1)
    event_summary: str = Field(min_length=1)
    action: ActionName
    target: str = Field(min_length=1)
    confidence: int = Field(ge=0, le=100)
    reason: str = Field(min_length=1)
    execute: bool = False


class AnalysisReport(BaseModel):
    """[FIX-LIVE-PIPELINE] Real-time analysis snapshot for operators."""

    total_events: int = Field(ge=0)
    elevated_events: int = Field(ge=0)
    signals: list[str] = Field(default_factory=list)
    events: list[ThreatEvent] = Field(default_factory=list)
    responses: list[AutoResponseDecision] = Field(default_factory=list)


class ResourceRecord(BaseModel):
    """Packaged runtime resource status."""

    path: str = Field(min_length=1)
    packaged: bool


class ResponsePlan(BaseModel):
    """Safe response action preview."""

    action: ActionName
    target: str = Field(min_length=1)
    execute: bool = False
    command: list[str] = Field(default_factory=list)
