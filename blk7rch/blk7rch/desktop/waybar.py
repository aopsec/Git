"""Waybar config writer — base and pentest IDS variants."""

from __future__ import annotations

import json
from pathlib import Path

from blk7rch.config.schema import BLK7Config
from blk7rch.utils.logger import log

# ---------------------------------------------------------------------------
# Base config
# ---------------------------------------------------------------------------

_BASE_CONFIG: dict = {
    "layer": "top",
    "position": "top",
    "height": 30,
    "modules-left": ["hyprland/workspaces"],
    "modules-center": ["clock"],
    "modules-right": ["tray"],
    "hyprland/workspaces": {
        "disable-scroll": True,
        "all-outputs": True,
        "format": "{id}",
    },
    "clock": {
        "format": "{:%H:%M  %Y-%m-%d}",
        "tooltip-format": "<big>{:%Y %B}</big>\n<tt><small>{calendar}</small></tt>",
    },
    "tray": {
        "spacing": 10,
    },
}

_BASE_STYLE = """\
* {
    border: none;
    border-radius: 0;
    font-family: "JetBrains Mono", monospace;
    font-size: 13px;
    min-height: 0;
}
window#waybar {
    background-color: rgba(26, 27, 38, 0.95);
    color: #cdd6f4;
}
#workspaces button {
    padding: 0 5px;
    color: #7f849c;
}
#workspaces button.active {
    color: #89b4fa;
    background-color: rgba(137, 180, 250, 0.15);
}
#clock, #tray {
    padding: 0 10px;
    color: #cdd6f4;
}
"""

# ---------------------------------------------------------------------------
# Pentest additions
# ---------------------------------------------------------------------------

_IDS_MODULE: dict = {
    "custom/ids": {
        "exec": (
            "count=$(grep -c 'ALERT' /var/log/suricata/fast.log 2>/dev/null || echo 0); "
            "echo \"\\ud83d\\udee1 IDS: $count\""
        ),
        "interval": 30,
        "format": "{}",
        "tooltip": False,
    }
}

_PENTEST_EXTRA_MODULES: dict = {
    "cpu": {
        "format": "CPU {usage}%",
        "interval": 5,
    },
    "memory": {
        "format": "MEM {}%",
        "interval": 5,
    },
    "network": {
        "format-wifi": "{essid} ({signalStrength}%)",
        "format-ethernet": "ETH {ipaddr}",
        "format-disconnected": "NO NET",
        "interval": 10,
    },
}

_PENTEST_STYLE_ADDITIONS = """\
#custom-ids {
    color: #f38ba8;
    padding: 0 10px;
    font-weight: bold;
}
#cpu, #memory, #network {
    padding: 0 8px;
    color: #a6e3a1;
}
"""


class WaybarConfig:
    """Writes Waybar configuration to the target system.

    Parameters
    ----------
    target:
        Mount point of the installed system.
    cfg:
        BLK7 configuration instance.
    username:
        Primary user — configs are written to their home directory.
    dry_run:
        When *True*, writes are skipped.
    """

    def __init__(
        self, target: Path, cfg: BLK7Config, username: str, dry_run: bool = False
    ) -> None:
        """Initialise the Waybar config writer."""
        self.target = target
        self.cfg = cfg
        self.username = username
        self.dry_run = dry_run

    def write(self) -> None:
        """Write ``~/.config/waybar/config`` and ``style.css`` for the primary user.

        The **pentest** variant adds a ``custom/ids`` module showing the
        Suricata alert count, plus CPU, memory, and network modules.
        """
        home = self.target / "home" / self.username
        config_dir = home / ".config" / "waybar"

        is_pentest = self.cfg.profile == "pentest" or self.cfg.workstation_mode == "pentest"

        config = dict(_BASE_CONFIG)
        style = _BASE_STYLE

        if is_pentest:
            config.update(_IDS_MODULE)
            config.update(_PENTEST_EXTRA_MODULES)
            config["modules-right"] = ["custom/ids", "cpu", "memory", "network", "clock", "tray"]
            style = _BASE_STYLE + _PENTEST_STYLE_ADDITIONS
            log.info("Waybar: writing pentest IDS variant")
        else:
            log.info("Waybar: writing base variant")

        if self.dry_run:
            log.dry(f"write {config_dir / 'config'}")
            log.dry(f"write {config_dir / 'style.css'}")
            return

        config_dir.mkdir(parents=True, exist_ok=True)
        try:
            (config_dir / "config").write_text(json.dumps(config, indent=2))
            (config_dir / "style.css").write_text(style)
        except OSError as exc:
            raise RuntimeError(f"Failed to write Waybar config to {config_dir}: {exc}") from exc
        log.ok(f"Waybar: config written to {config_dir}")
