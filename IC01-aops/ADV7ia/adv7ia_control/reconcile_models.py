"""Typed models for OpenHands live reconcile planning."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
DiffClass = Literal["live_patchable", "recreate_required", "blocked"]
ApplyMode = Literal["auto", "api", "file"]
InspectionStatus = Literal["ok", "missing_container", "unavailable"]


class PortBinding(BaseModel):
    """Describe one published container port."""

    host_ip: str = "127.0.0.1"
    host_port: int
    container_port: int


class ContainerSpec(BaseModel):
    """Capture the Docker-managed parts of the OpenHands deployment."""

    service_name: str = "openhands-app"
    container_name: str = "openhands-app"
    compose_file: str = "deploy/openhands/compose.yaml"
    image: str = "docker.openhands.dev/openhands/openhands:1.6"
    restart_policy: str = "unless-stopped"
    network_mode: str = "bridge"
    privileged: bool = False
    published_ports: list[PortBinding] = Field(default_factory=list)
    required_env: dict[str, str] = Field(default_factory=dict)
    required_mounts: list[str] = Field(default_factory=list)
    required_extra_hosts: list[str] = Field(default_factory=list)
    required_security_opt: list[str] = Field(default_factory=list)
    command: list[str] = Field(default_factory=lambda: ["serve"])


class ManagedSetting(BaseModel):
    """Resolve one OpenHands setting from a literal or an environment variable."""

    mode: Literal["literal", "env"] = "literal"
    value: JsonValue | None = None
    env_var: str | None = None
    default: JsonValue | None = None


class OpenHandsSettingsSpec(BaseModel):
    """Describe the managed subset of persisted OpenHands settings."""

    settings_file: str = "${HOME}/.openhands/settings.json"
    apply_mode: ApplyMode = "auto"
    managed_settings: dict[str, ManagedSetting] = Field(default_factory=dict)


class CutoverPolicy(BaseModel):
    """Keep reconfiguration behavior explicit and reviewable."""

    allow_recreate: bool = True
    require_proxy: bool = True
    recreate_timeout_seconds: int = 120
    restart_conversations_on_llm_change: bool = True


class OpenHandsDesiredState(BaseModel):
    """Top-level desired state for live OpenHands reconciliation."""

    container_spec: ContainerSpec = Field(default_factory=ContainerSpec)
    openhands_settings: OpenHandsSettingsSpec = Field(default_factory=OpenHandsSettingsSpec)
    cutover_policy: CutoverPolicy = Field(default_factory=CutoverPolicy)


class LiveRuntime(BaseModel):
    """Represent the live OpenHands container and persisted settings."""

    container_name: str
    inspection_status: InspectionStatus = "unavailable"
    running: bool = False
    image: str = ""
    restart_policy: str = ""
    network_mode: str = ""
    privileged: bool = False
    published_ports: list[PortBinding] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    mounts: list[str] = Field(default_factory=list)
    extra_hosts: list[str] = Field(default_factory=list)
    security_opt: list[str] = Field(default_factory=list)
    command: list[str] = Field(default_factory=list)
    settings_file: str = ""
    settings_source: Literal["file", "missing"] = "missing"
    settings: dict[str, JsonValue] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ReconcileDiff(BaseModel):
    """Describe one drift item and how it should be remediated."""

    scope: Literal["container_spec", "openhands_settings", "security_policy"]
    key: str
    classification: DiffClass
    current: str
    desired: str
    reason: str


class ReconcilePlan(BaseModel):
    """Capture one reconcile planning result."""

    desired: OpenHandsDesiredState
    live: LiveRuntime
    diffs: list[ReconcileDiff] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    compliant: bool = True
    can_apply: bool = True
    settings_apply_mode: ApplyMode = "auto"


class ApplyResult(BaseModel):
    """Return the reconcile plan plus the executed steps."""

    plan: ReconcilePlan
    executed_steps: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
