"""Hyprland config writer — base and pentest variants."""

from __future__ import annotations

from pathlib import Path

from blk7rch.config.schema import BLK7Config
from blk7rch.utils.logger import log

_BASE_CONFIG_TEMPLATE = """\
# BLK7rch Hyprland configuration — base variant
monitor=,preferred,auto,1

exec-once=waybar
exec-once=mako

input {{
    kb_layout={kb_layout}
    follow_mouse=1
    sensitivity=0
}}

general {{
    gaps_in=5
    gaps_out=10
    border_size=2
    col.active_border=rgba(33ccffee) rgba(00ff99ee) 45deg
    col.inactive_border=rgba(595959aa)
    layout=dwindle
}}

decoration {{
    rounding=8
    drop_shadow=yes
    shadow_range=4
    shadow_render_power=3
}}

animations {{
    enabled=yes
    bezier=myBezier,0.05,0.9,0.1,1.05
    animation=windows,1,7,myBezier
    animation=border,1,10,default
    animation=fade,1,7,default
    animation=workspaces,1,6,default
}}

dwindle {{
    pseudotile=yes
    preserve_split=yes
}}

# Keybinds
$mod=SUPER
bind=$mod,Return,exec,foot
bind=$mod,D,exec,wofi --show drun
bind=$mod,Q,killactive
bind=$mod,M,exit
bind=$mod,F,fullscreen
bind=$mod,V,togglefloating
bind=$mod,P,pseudo
bind=$mod,J,togglesplit

# Focus movement
bind=$mod,left,movefocus,l
bind=$mod,right,movefocus,r
bind=$mod,up,movefocus,u
bind=$mod,down,movefocus,d

# Workspace switching
bind=$mod,1,workspace,1
bind=$mod,2,workspace,2
bind=$mod,3,workspace,3
bind=$mod,4,workspace,4
bind=$mod,5,workspace,5
bind=$mod,6,workspace,6
bind=$mod,7,workspace,7
bind=$mod,8,workspace,8
bind=$mod,9,workspace,9
bind=$mod,0,workspace,10

# Move window to workspace
bind=$mod SHIFT,1,movetoworkspace,1
bind=$mod SHIFT,2,movetoworkspace,2
bind=$mod SHIFT,3,movetoworkspace,3
bind=$mod SHIFT,4,movetoworkspace,4
bind=$mod SHIFT,5,movetoworkspace,5
bind=$mod SHIFT,6,movetoworkspace,6
bind=$mod SHIFT,7,movetoworkspace,7
bind=$mod SHIFT,8,movetoworkspace,8
bind=$mod SHIFT,9,movetoworkspace,9
bind=$mod SHIFT,0,movetoworkspace,10

# Screenshot
bind=,Print,exec,grim -g "$(slurp)" - | wl-copy
"""

_PENTEST_EXTRA = """\
# ── Pentest variant additions ────────────────────────────────────────────────

general {{
    col.active_border=rgba(ff0000ee) rgba(ff6600ee) 45deg
}}

# Resize with SUPER+CTRL+arrows
binde=$mod CTRL,right,resizeactive,30 0
binde=$mod CTRL,left,resizeactive,-30 0
binde=$mod CTRL,up,resizeactive,0 -30
binde=$mod CTRL,down,resizeactive,0 30

# Pentest quick-launchers
bind=$mod SHIFT,S,exec,foot -e sudo tail -f /var/log/snort/alert.fast
bind=$mod SHIFT,M,exec,foot -e sudo journalctl -fu suricata
bind=$mod SHIFT,W,exec,wireshark
bind=$mod SHIFT,B,exec,firefox --private-window
bind=$mod SHIFT,H,exec,foot -e htop
bind=$mod SHIFT,Return,exec,foot -e sudo -i
"""


class HyprlandConfig:
    """Writes Hyprland configuration to the target system.

    Parameters
    ----------
    target:
        Mount point of the installed system.
    cfg:
        BLK7 configuration instance (uses ``cfg.keymap`` and ``cfg.profile``).
    username:
        Primary user — config is written to their home directory.
    dry_run:
        When *True*, writes are skipped.
    """

    def __init__(
        self, target: Path, cfg: BLK7Config, username: str, dry_run: bool = False
    ) -> None:
        """Initialise the Hyprland config writer."""
        self.target = target
        self.cfg = cfg
        self.username = username
        self.dry_run = dry_run

    def write(self) -> None:
        """Write ``~/.config/hypr/hyprland.conf`` for the primary user.

        The **pentest** variant appends orange/red border colours and
        security quick-launcher keybinds to the base config.
        """
        home = self.target / "home" / self.username
        config_dir = home / ".config" / "hypr"

        base = _BASE_CONFIG_TEMPLATE.format(kb_layout=self.cfg.keymap)

        if self.cfg.profile == "pentest" or self.cfg.workstation_mode == "pentest":
            content = base + _PENTEST_EXTRA
            log.info("Hyprland: writing pentest config variant")
        else:
            content = base
            log.info("Hyprland: writing base config variant")

        if self.dry_run:
            log.dry(f"write {config_dir / 'hyprland.conf'}")
            return

        config_dir.mkdir(parents=True, exist_ok=True)
        try:
            (config_dir / "hyprland.conf").write_text(content)
        except OSError as exc:
            raise RuntimeError(f"Failed to write Hyprland config to {config_dir}: {exc}") from exc
        log.ok(f"Hyprland: config written to {config_dir / 'hyprland.conf'}")
