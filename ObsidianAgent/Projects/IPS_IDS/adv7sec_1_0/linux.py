"""Linux target discovery and runtime probes."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

from adv7sec_1_0.models import Capability, RuntimeTarget, SupportTier


def read_os_release() -> dict[str, str]:
    """Return normalized /etc/os-release values."""
    os_release = Path("/etc/os-release")
    values: dict[str, str] = {}
    if not os_release.is_file():
        return values
    for line in os_release.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, raw_value = line.split("=", 1)
        values[key] = raw_value.strip().strip('"')
    return values


def detect_init_system() -> str:
    """Infer the current init system."""
    comm = Path("/proc/1/comm")
    if comm.is_file():
        return comm.read_text(encoding="utf-8").strip()
    return "unknown"


def detect_runtime_target() -> RuntimeTarget:
    """Build a cross-distro runtime target model."""
    values = read_os_release()
    distro_id = values.get("ID", "unknown")
    distro_name = values.get("PRETTY_NAME", distro_id)
    package_managers = {
        "arch": "pacman",
        "manjaro": "pacman",
        "endeavouros": "pacman",
        "ubuntu": "apt",
        "debian": "apt",
        "fedora": "dnf",
        "rhel": "dnf",
        "rocky": "dnf",
        "almalinux": "dnf",
        "opensuse-tumbleweed": "zypper",
    }
    support_tiers: dict[str, SupportTier] = {
        "arch": "native",
        "manjaro": "adapted",
        "endeavouros": "adapted",
        "ubuntu": "adapted",
        "debian": "adapted",
        "fedora": "adapted",
        "rhel": "experimental",
        "rocky": "experimental",
        "almalinux": "experimental",
        "opensuse-tumbleweed": "experimental",
        "unknown": "experimental",
    }
    return RuntimeTarget(
        distro_id=distro_id,
        distro_name=distro_name,
        package_manager=package_managers.get(distro_id, "manual"),
        init_system=detect_init_system(),
        support_tier=support_tiers.get(distro_id, "experimental"),
        kernel_release=platform.release(),
    )


def probe_capabilities() -> list[Capability]:
    """Probe host capabilities relevant to ADV7Sec 1.0."""
    probes = {
        "systemctl": shutil.which("systemctl"),
        "journalctl": shutil.which("journalctl"),
        "auditctl": shutil.which("auditctl"),
        "suricata": shutil.which("suricata"),
        "falco": shutil.which("falco"),
        "zeekctl": shutil.which("zeekctl"),
        "clamonacc": shutil.which("clamonacc"),
    }
    btf_path = "/sys/kernel/btf/vmlinux"
    capabilities = [
        Capability(
            name=name,
            available=bool(path),
            detail=path or "not found on PATH",
        )
        for name, path in probes.items()
    ]
    capabilities.append(
        Capability(
            name="btf",
            available=Path(btf_path).exists(),
            detail=btf_path if Path(btf_path).exists() else "missing",
        )
    )
    capabilities.append(
        Capability(
            name="root",
            available=os.geteuid() == 0,
            detail="running as root" if os.geteuid() == 0 else "run with sudo for apply/response",
        )
    )
    return capabilities
