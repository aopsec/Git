"""Live OpenHands runtime inspection helpers."""
from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

from adv7ia_control.reconcile_models import (
    InspectionStatus,
    JsonValue,
    LiveRuntime,
    OpenHandsDesiredState,
    PortBinding,
)

CommandRunner = Callable[[list[str]], str]


def inspect_live_runtime(
    root: Path,
    desired: OpenHandsDesiredState,
    command_runner: CommandRunner | None = None,
) -> LiveRuntime:
    """Collect the live container snapshot and the persisted settings."""
    runtime = LiveRuntime(container_name=desired.container_spec.container_name)
    runtime.settings_file = expand_text(desired.openhands_settings.settings_file, root)
    settings_path = Path(runtime.settings_file)
    if settings_path.is_file():
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            runtime.settings = cast(dict[str, JsonValue], payload)
            runtime.settings_source = "file"
        else:
            runtime.notes.append(f"settings file `{settings_path}` does not contain a JSON object")
    else:
        runtime.notes.append(f"settings file `{settings_path}` is missing")
    runner = command_runner or run_command
    try:
        inspect_raw = runner(["docker", "inspect", desired.container_spec.container_name])
    except FileNotFoundError:
        runtime.notes.append("docker binary is unavailable; live container inspection skipped")
        return runtime
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip()
        runtime.inspection_status = classify_inspect_failure(detail)
        label = f"container `{desired.container_spec.container_name}` is absent or not inspectable"
        if runtime.inspection_status == "missing_container":
            label = f"container `{desired.container_spec.container_name}` is missing"
        runtime.notes.append(f"{label}: {detail}" if detail else label)
        return runtime
    try:
        inspect_payload = json.loads(inspect_raw)
    except json.JSONDecodeError:
        runtime.notes.append("docker inspect returned invalid JSON")
        return runtime
    if not isinstance(inspect_payload, list) or not inspect_payload:
        runtime.notes.append("docker inspect returned an unexpected payload")
        return runtime
    container = inspect_payload[0]
    config = _as_dict(container.get("Config"))
    host_config = _as_dict(container.get("HostConfig"))
    state = _as_dict(container.get("State"))
    runtime.running = str(state.get("Status", "")) == "running"
    runtime.image = str(config.get("Image", ""))
    runtime.restart_policy = str(_as_dict(host_config.get("RestartPolicy")).get("Name", ""))
    runtime.network_mode = str(host_config.get("NetworkMode", ""))
    runtime.privileged = bool(host_config.get("Privileged", False))
    runtime.env = parse_env(cast(list[str], config.get("Env", [])))
    runtime.mounts = [str(item) for item in cast(list[str], host_config.get("Binds", []))]
    runtime.extra_hosts = sorted(
        str(item) for item in cast(list[str], host_config.get("ExtraHosts", []))
    )
    runtime.security_opt = [
        str(item) for item in cast(list[str], host_config.get("SecurityOpt", []))
    ]
    runtime.command = [str(item) for item in cast(list[str], config.get("Cmd", []))]
    runtime.published_ports = parse_port_bindings(host_config.get("PortBindings"))
    runtime.inspection_status = "ok"
    return runtime


def expand_text(value: str, root: Path) -> str:
    """Expand repo-local and shell environment placeholders."""
    rendered = value.replace("${ADV7IA_ROOT}", str(root))
    return os.path.expandvars(os.path.expanduser(rendered))


def parse_port_bindings(payload: object) -> list[PortBinding]:
    """Normalize Docker port bindings into a stable list."""
    bindings = _as_dict(payload)
    result: list[PortBinding] = []
    for container_port, mapping_list in sorted(bindings.items()):
        port_number = int(str(container_port).split("/", maxsplit=1)[0])
        if not isinstance(mapping_list, list):
            continue
        for mapping in mapping_list:
            mapping_dict = _as_dict(mapping)
            result.append(
                PortBinding(
                    host_ip=normalize_host_ip(str(mapping_dict.get("HostIp", ""))),
                    host_port=int(str(mapping_dict.get("HostPort", "0"))),
                    container_port=port_number,
                )
            )
    return sorted(result, key=lambda item: (item.container_port, item.host_ip, item.host_port))


def parse_env(items: list[str]) -> dict[str, str]:
    """Turn Docker env entries into a dictionary."""
    env: dict[str, str] = {}
    for item in items:
        key, _, value = item.partition("=")
        env[key] = value
    return env


def normalize_host_ip(value: str) -> str:
    """Treat an empty Docker bind host as a public publish."""
    return value or "0.0.0.0"


def classify_inspect_failure(detail: str) -> InspectionStatus:
    """Classify whether Docker inspection failed safely or unsafely."""
    lowered = detail.lower()
    if "no such object" in lowered or "no such container" in lowered:
        return "missing_container"
    return "unavailable"


def run_command(args: list[str]) -> str:
    """Run one local command and return stdout."""
    completed = subprocess.run(args, capture_output=True, check=True, text=True)
    return completed.stdout


def _as_dict(value: object) -> dict[str, object]:
    """Return a dictionary-like object or an empty mapping."""
    return cast(dict[str, object], value) if isinstance(value, dict) else {}
