"""Default BLK7Config values for each installation profile."""

from __future__ import annotations

from blk7rch.config.schema import BLK7Config

# ---------------------------------------------------------------------------
# Profile presets
# ---------------------------------------------------------------------------

DEFAULTS_MINIMAL: dict = {
    "hostname": "blk7arch",
    "username": "user",
    "timezone": "America/Sao_Paulo",
    "locale": "en_US.UTF-8",
    "keymap": "us",
    "bootloader": "grub",
    "profile": "minimal",
    "workstation_mode": "none",
    "enable_blackarch": False,
    "enable_ids": False,
    "ids_home_net": "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]",
    "ids_snort_profile": "balanced",
    "ids_mode": "minimal-local",
    "allow_ssh_inbound": False,
    "wifi_backend": "nm",
    "enable_gdm": False,
    "auto_reboot": True,
    "root_lv_size": "30G",
    "swap_lv_size": "4G",
}

DEFAULTS_WORKSTATION: dict = {
    **DEFAULTS_MINIMAL,
    "profile": "workstation",
    "workstation_mode": "base",
    "enable_gdm": True,
    "root_lv_size": "50G",
    "swap_lv_size": "8G",
}

DEFAULTS_PENTEST: dict = {
    **DEFAULTS_WORKSTATION,
    "profile": "pentest",
    "workstation_mode": "pentest",
    "enable_blackarch": True,
    "enable_ids": True,
    "allow_ssh_inbound": False,
    "ids_snort_profile": "balanced",
    "ids_mode": "minimal-local",
    "root_lv_size": "60G",
    "swap_lv_size": "8G",
}

_PROFILE_MAP: dict[str, dict] = {
    "minimal": DEFAULTS_MINIMAL,
    "core": DEFAULTS_MINIMAL,
    "workstation": DEFAULTS_WORKSTATION,
    "pentest": DEFAULTS_PENTEST,
}


def defaults_for_profile(profile: str) -> dict:
    """Return the default values dict for *profile*.

    Parameters
    ----------
    profile:
        One of ``minimal``, ``core``, ``workstation``, ``pentest``.

    Returns
    -------
    dict
        A copy of the defaults mapping for the given profile.

    Raises
    ------
    ValueError
        If *profile* is not a recognised profile name.
    """
    if profile not in _PROFILE_MAP:
        raise ValueError(f"Unknown profile '{profile}'. Valid: {list(_PROFILE_MAP)}")
    return dict(_PROFILE_MAP[profile])


def make_default_config(profile: str = "workstation") -> BLK7Config:
    """Instantiate a :class:`~blk7rch.config.schema.BLK7Config` with default values.

    Parameters
    ----------
    profile:
        Profile preset to use as the base.
    """
    return BLK7Config(**defaults_for_profile(profile))
