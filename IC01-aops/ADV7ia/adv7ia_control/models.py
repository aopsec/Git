"""Typed models for the ADV7ia control mesh."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["queued", "active", "blocked", "closed", "dead_letter"]
SessionStatus = Literal["active", "compact_pending", "rolled", "closed"]
CheckpointPhase = Literal[
    "intake",
    "plan",
    "execute",
    "verify",
    "summarize",
    "compact",
    "close",
]


class RoleConfig(BaseModel):
    """Describe one controller role in the mesh."""

    name: str
    description: str
    enabled: bool = True


class MeshEndpoints(BaseModel):
    """Record the local control-mesh endpoints."""

    openhands_local_url: str = "http://127.0.0.1:3000"
    openhands_proxy_url: str = "https://adv7ia-control.home.arpa:8443"
    lm_studio_url: str = "http://127.0.0.1:1234/v1"
    qdrant_url: str = "http://127.0.0.1:6333"
    obsidian_root: str = "vault"


class TokenPolicy(BaseModel):
    """Keep token rollover thresholds explicit and reviewable."""

    warning_ratio: float = 0.80
    freeze_ratio: float = 0.90
    compact_ratio: float = 0.95
    context_window: int = 32768


class SecurityPolicy(BaseModel):
    """Centralize the security gates for the local mesh."""

    openhands_bind: str = "127.0.0.1:3000:3000"
    allow_host_network: bool = False
    allow_privileged: bool = False
    require_client_auth: bool = True
    lan_allowlist: list[str] = Field(
        default_factory=lambda: [
            "127.0.0.0/8",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
        ]
    )
    gated_actions: list[str] = Field(
        default_factory=lambda: ["edit", "network", "secret", "privileged", "destructive"]
    )
    max_recursion_depth: int = 3
    max_retry_count: int = 2


class ControlPolicy(BaseModel):
    """Top-level policy file for the controller."""

    policy_name: str = "adv7ia-control-mesh"
    token_policy: TokenPolicy = Field(default_factory=TokenPolicy)
    security_policy: SecurityPolicy = Field(default_factory=SecurityPolicy)
    endpoints: MeshEndpoints = Field(default_factory=MeshEndpoints)
    roles: list[RoleConfig] = Field(default_factory=list)


class TaskRecord(BaseModel):
    """Represent one task in the recursive execution graph."""

    task_id: str
    title: str
    objective: str
    status: TaskStatus = "queued"
    parent_task_id: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    branch_depth: int = 0
    retry_count: int = 0
    current_session_id: str | None = None
    risky_actions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    last_checkpoint_id: str | None = None
    assigned_role: str = "planner"


class SessionRecord(BaseModel):
    """Track one live or rolled execution session."""

    session_id: str
    task_id: str
    status: SessionStatus = "active"
    current_role: str = "planner"
    model: str = "lm_studio/qwen3-coder-local"
    prompt_tokens: int = 0
    context_window: int = 32768
    compaction_count: int = 0
    checkpoint_ids: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    opened_at: str
    parent_session_id: str | None = None
    last_compacted_at: str | None = None
    summary_note: str | None = None


class CheckpointRecord(BaseModel):
    """Capture one checkpoint in the recursive control loop."""

    checkpoint_id: str
    task_id: str
    session_id: str
    phase: CheckpointPhase
    summary: str
    decisions: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    created_at: str


class GateDecision(BaseModel):
    """Explain whether a proposed action must stop for approval."""

    action: str
    requires_approval: bool
    reason: str


class MeshStatus(BaseModel):
    """Aggregate the live state into one renderable snapshot."""

    root: str
    policy: ControlPolicy
    active_tasks: list[TaskRecord] = Field(default_factory=list)
    active_sessions: list[SessionRecord] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    pending_gates: list[GateDecision] = Field(default_factory=list)
