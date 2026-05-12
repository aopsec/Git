"""Cross-distro package and service adapters."""

from __future__ import annotations

from adv7sec_1_0.feature_catalog import iter_feature_specs
from adv7sec_1_0.models import BackendPlan, PackageAction, RuntimeTarget, ServiceBinding


def _package_command(package_manager: str, packages: list[str]) -> tuple[list[str], dict[str, str]]:
    if not packages:
        return [], {}
    if package_manager == "pacman":
        return ["pacman", "-S", "--needed", "--noconfirm", *packages], {}
    if package_manager == "apt":
        return ["apt-get", "install", "-y", *packages], {"DEBIAN_FRONTEND": "noninteractive"}
    if package_manager == "dnf":
        return ["dnf", "install", "-y", *packages], {}
    if package_manager == "zypper":
        return ["zypper", "--non-interactive", "install", *packages], {}
    return [], {}


def build_backend_plan(target: RuntimeTarget) -> BackendPlan:
    """[FIX-LINUX-ADAPTERS] Materialize install/service actions from the unified catalog."""

    package_actions: list[PackageAction] = []
    service_manager = "systemctl" if target.init_system == "systemd" else target.init_system
    service_bindings: list[ServiceBinding] = []
    for spec in iter_feature_specs():
        packages = spec.packages_by_manager.get(target.package_manager, [])
        command, environment = _package_command(target.package_manager, packages)
        if packages:
            status = "native"
        elif spec.manual_note is not None:
            status = f"manual: {spec.manual_note}"
        else:
            status = f"unsupported on {target.package_manager}"
        package_actions.append(
            PackageAction(
                feature=spec.name,
                packages=packages,
                command=command,
                environment=environment,
                status=status,
            )
        )
        if spec.service_unit is None:
            continue
        service_bindings.append(
            ServiceBinding(
                feature=spec.name,
                unit=spec.service_unit,
                enable_command=["systemctl", "enable", "--now", spec.service_unit]
                if service_manager == "systemctl"
                else [],
            )
        )
    return BackendPlan(
        package_manager=target.package_manager,
        service_manager=service_manager,
        package_actions=package_actions,
        service_bindings=service_bindings,
    )
