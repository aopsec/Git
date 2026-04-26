"""Unified feature catalog for install, backend, and runtime planning."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FeatureSpec(BaseModel):
    """[FIX-FEATURE-CATALOG] Single source of truth for one installable feature."""

    name: str = Field(min_length=1)
    packages_by_manager: dict[str, list[str]] = Field(default_factory=dict)
    resources: list[tuple[str, str]] = Field(default_factory=list)
    directories: list[tuple[str, int]] = Field(default_factory=list)
    validations: list[list[str]] = Field(default_factory=list)
    service_unit: str | None = None
    manual_note: str | None = None


_FEATURE_SPECS: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        name="auditd",
        packages_by_manager={
            "pacman": ["audit"],
            "apt": ["auditd", "audispd-plugins"],
            "dnf": ["audit"],
            "zypper": ["audit"],
        },
        resources=[
            (
                "etc/audit/rules.d/50-persistence.rules",
                "etc/audit/rules.d/50-persistence.rules",
            )
        ],
        validations=[["augenrules", "--check"], ["auditctl", "-s"]],
        service_unit="auditd.service",
    ),
    FeatureSpec(
        name="falco",
        resources=[
            ("etc/falco/falco.local.yaml", "etc/falco/falco.local.yaml"),
            ("etc/falco/rules.d/workstation.yaml", "etc/falco/rules.d/workstation.yaml"),
        ],
        manual_note="Use pacote oficial ou instalacao manual do fornecedor.",
    ),
    FeatureSpec(
        name="kunai",
        resources=[
            ("etc/kunai/rules/workstation.kunai", "etc/kunai/rules/workstation.kunai"),
            ("etc/systemd/system/kunai.service", "etc/systemd/system/kunai.service"),
        ],
        manual_note="Instalacao manual ou build local controlado permanece obrigatorio.",
    ),
    FeatureSpec(
        name="suricata",
        packages_by_manager={
            "pacman": ["suricata"],
            "apt": ["suricata"],
            "dnf": ["suricata"],
            "zypper": ["suricata"],
        },
        resources=[
            ("etc/suricata/eve-minimal.yaml", "etc/suricata/eve-minimal.yaml"),
            ("etc/suricata/disable.conf", "etc/suricata/disable.conf"),
            ("etc/suricata/ipsids-overrides.yaml", "etc/suricata/ipsids-overrides.yaml"),
            (
                "etc/systemd/system/suricata.service.d/ipsids.conf",
                "etc/systemd/system/suricata.service.d/ipsids.conf",
            ),
            ("usr/local/sbin/ipsids-suricata-run.sh", "usr/local/sbin/ipsids-suricata-run.sh"),
        ],
        directories=[("var/log/suricata", 0o750)],
        validations=[["/usr/local/sbin/ipsids-suricata-run.sh", "--test"]],
        service_unit="suricata.service",
    ),
    FeatureSpec(
        name="unbound",
        packages_by_manager={
            "pacman": ["unbound"],
            "apt": ["unbound"],
            "dnf": ["unbound"],
            "zypper": ["unbound"],
        },
        resources=[
            (
                "etc/unbound/unbound.conf.d/dnstap.conf",
                "etc/unbound/unbound.conf.d/dnstap.conf",
            )
        ],
        directories=[("run/unbound", 0o755)],
        validations=[["unbound-checkconf"]],
        service_unit="unbound.service",
    ),
    FeatureSpec(
        name="aide",
        packages_by_manager={
            "pacman": ["aide"],
            "apt": ["aide"],
            "dnf": ["aide"],
            "zypper": ["aide"],
        },
        resources=[
            ("etc/aide/aide.conf", "etc/aide.conf"),
            ("etc/pacman.d/hooks/90-aide-update.hook", "etc/pacman.d/hooks/90-aide-update.hook"),
            ("etc/systemd/system/aide-check.service", "etc/systemd/system/aide-check.service"),
            ("etc/systemd/system/aide-check.timer", "etc/systemd/system/aide-check.timer"),
            (
                "usr/local/sbin/ipsids-aide-pacman-hook.sh",
                "usr/local/sbin/ipsids-aide-pacman-hook.sh",
            ),
        ],
        directories=[("var/lib/aide", 0o755)],
        validations=[["aide", "--init"]],
    ),
    FeatureSpec(
        name="clamav",
        packages_by_manager={
            "pacman": ["clamav"],
            "apt": ["clamav", "clamav-daemon", "clamav-freshclam"],
            "dnf": ["clamav", "clamav-update", "clamav-scanner-systemd"],
            "zypper": ["clamav"],
        },
        directories=[("var/log/clamav", 0o750)],
        service_unit="clamav-clamonacc.service",
    ),
    FeatureSpec(
        name="lynis",
        packages_by_manager={
            "pacman": ["lynis"],
            "apt": ["lynis"],
            "dnf": ["lynis"],
            "zypper": ["lynis"],
        },
        resources=[
            ("etc/systemd/system/lynis-audit.service", "etc/systemd/system/lynis-audit.service"),
            ("etc/systemd/system/lynis-audit.timer", "etc/systemd/system/lynis-audit.timer"),
            ("etc/systemd/system/chkrootkit.service", "etc/systemd/system/chkrootkit.service"),
            ("etc/systemd/system/chkrootkit.timer", "etc/systemd/system/chkrootkit.timer"),
        ],
    ),
)

_FEATURE_INDEX: dict[str, FeatureSpec] = {spec.name: spec for spec in _FEATURE_SPECS}


def feature_choices() -> tuple[str, ...]:
    """Return the valid CLI feature choices."""

    return tuple(spec.name for spec in _FEATURE_SPECS)


def iter_feature_specs() -> tuple[FeatureSpec, ...]:
    """Return the full feature catalog."""

    return _FEATURE_SPECS


def get_feature_spec(name: str) -> FeatureSpec:
    """Return one feature spec from the unified catalog."""

    return _FEATURE_INDEX[name]


def selected_feature_specs(feature: str) -> list[FeatureSpec]:
    """Return one or all feature specs based on the CLI selector."""

    return list(_FEATURE_SPECS if feature == "all" else (get_feature_spec(feature),))
