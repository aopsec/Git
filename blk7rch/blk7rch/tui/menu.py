"""BLK7Menu — extends archinstall GlobalMenu with BLK7-specific options."""

from __future__ import annotations

from blk7rch.config.schema import BLK7Config
from blk7rch.utils.logger import log

try:
    from archinstall.lib.global_menu import GlobalMenu
    _ARCHINSTALL_TUI_AVAILABLE = True
except ImportError:
    GlobalMenu = object  # type: ignore[misc,assignment]
    _ARCHINSTALL_TUI_AVAILABLE = False

try:
    from archinstall.tui import MenuItem, MenuItemGroup
    _TUI_ITEMS_AVAILABLE = True
except ImportError:
    try:
        from archinstall.lib.menu import MenuItem, MenuItemGroup  # type: ignore[no-redef]
        _TUI_ITEMS_AVAILABLE = True
    except ImportError:
        _TUI_ITEMS_AVAILABLE = False

_PROFILES = ["minimal", "core", "workstation", "pentest"]


class BLK7Menu(GlobalMenu):  # type: ignore[misc]
    """BLK7 installer menu — adds security/pentest options to archinstall's menu.

    All built-in archinstall menu items (language, keymap, timezone, locale,
    disk, encryption, users) remain accessible through the parent class.

    Parameters
    ----------
    data_store:
        Shared data storage dict passed to the archinstall GlobalMenu.
    cfg:
        BLK7 configuration instance updated in-place by menu interactions.
    """

    def __init__(self, data_store: dict, cfg: BLK7Config) -> None:
        """Initialise the BLK7 menu."""
        self._blk7_cfg = cfg
        super().__init__(data_store)

    def setup_selection_menu_options(self) -> None:
        """Register all menu options — archinstall built-ins + BLK7 additions.

        The parent class registers: language, keyboard layout, timezone, locale,
        mirror region, disk, encryption, swap, hostname, root password, user,
        profile, audio, network config, additional packages, timezone, NTP,
        bootloader.

        BLK7 adds: profile selector, BlackArch toggle, IDS toggle, security
        options sub-menu.
        """
        # Inherit all standard archinstall menu items
        super().setup_selection_menu_options()

        # BLK7-specific items
        self._add_blk7_items()

    def _add_blk7_items(self) -> None:
        """Append BLK7-specific items to the menu option map."""
        if not _TUI_ITEMS_AVAILABLE:
            log.warn("archinstall TUI items not available — BLK7 menu items skipped")
            return

        self._menu_options["blk7_profile"] = MenuItem(  # type: ignore[index]
            text="BLK7 Profile",
            action=self._select_blk7_profile,
            preview_action=lambda _: self._blk7_cfg.profile,
        )

        self._menu_options["enable_blackarch"] = MenuItem(  # type: ignore[index]
            text="Enable BlackArch Repository",
            action=self._toggle_blackarch,
            preview_action=lambda _: "enabled" if self._blk7_cfg.enable_blackarch else "disabled",
        )

        self._menu_options["enable_ids"] = MenuItem(  # type: ignore[index]
            text="IDS/IPS (Snort + Suricata)",
            action=self._toggle_ids,
            preview_action=lambda _: "enabled" if self._blk7_cfg.enable_ids else "disabled",
        )

        self._menu_options["security_options"] = MenuItem(  # type: ignore[index]
            text="Security Options",
            action=self._security_submenu,
            preview_action=lambda _: self._security_summary(),
        )

    # ------------------------------------------------------------------
    # Action callbacks
    # ------------------------------------------------------------------

    def _select_blk7_profile(self, preset: str | None = None) -> str:
        """Show a selection menu for the BLK7 installation profile.

        Parameters
        ----------
        preset:
            Pre-selected value (used in unattended mode).

        Returns
        -------
        str
            The selected profile name.
        """
        if preset is not None:
            self._blk7_cfg.profile = preset
            return preset

        try:
            from archinstall.tui import SelectMenu, Alignment, FrameProperties
            result = SelectMenu(
                MenuItemGroup.create_simple(_PROFILES),
                header="Select BLK7 installation profile",
                alignment=Alignment.CENTER,
                frame=FrameProperties.min("BLK7 Profile"),
            ).run()
            if result and result.item():
                chosen = str(result.item())
                self._blk7_cfg.profile = chosen
                return chosen
        except Exception:  # noqa: BLE001 — archinstall TUI may be unavailable; fall back silently
            log.info("Profile selector TUI unavailable — using current profile")

        return self._blk7_cfg.profile

    def _toggle_blackarch(self, value: bool | None = None) -> bool:
        """Toggle the BlackArch repository option.

        Parameters
        ----------
        value:
            When provided, sets the option directly (unattended mode).

        Returns
        -------
        bool
            New state of ``enable_blackarch``.
        """
        if value is not None:
            self._blk7_cfg.enable_blackarch = value
            return value

        self._blk7_cfg.enable_blackarch = not self._blk7_cfg.enable_blackarch
        state = "enabled" if self._blk7_cfg.enable_blackarch else "disabled"
        log.info(f"BlackArch repository: {state}")
        return self._blk7_cfg.enable_blackarch

    def _toggle_ids(self, value: bool | None = None) -> bool:
        """Toggle the IDS/IPS option (Snort + Suricata).

        Parameters
        ----------
        value:
            When provided, sets the option directly (unattended mode).

        Returns
        -------
        bool
            New state of ``enable_ids``.
        """
        if value is not None:
            self._blk7_cfg.enable_ids = value
            return value

        self._blk7_cfg.enable_ids = not self._blk7_cfg.enable_ids
        state = "enabled" if self._blk7_cfg.enable_ids else "disabled"
        log.info(f"IDS/IPS (Snort + Suricata): {state}")
        return self._blk7_cfg.enable_ids

    def _security_submenu(self, _preset: object = None) -> None:
        """Display a sub-menu for security options.

        Options:
        * Toggle SSH inbound (UFW port 22)
        * IDS mode (minimal-local / managed-rules)
        * Snort profile (balanced / strict)
        * IDS HOME_NET CIDR
        """
        try:
            from archinstall.tui import SelectMenu, Alignment, FrameProperties, MenuItemGroup

            options = [
                f"SSH inbound: {'allow' if self._blk7_cfg.allow_ssh_inbound else 'deny'}",
                f"IDS mode: {self._blk7_cfg.ids_mode}",
                f"Snort profile: {self._blk7_cfg.ids_snort_profile}",
                f"IDS HOME_NET: {self._blk7_cfg.ids_home_net}",
            ]
            SelectMenu(
                MenuItemGroup.create_simple(options),
                header="Security Options — press Enter to change, ESC to go back",
                alignment=Alignment.CENTER,
                frame=FrameProperties.min("Security"),
            ).run()
        except Exception:  # noqa: BLE001 — archinstall security submenu may be unavailable
            log.warn("Security submenu unavailable — edit config file directly")

    def _security_summary(self) -> str:
        """Return a one-line summary of current security settings."""
        return (
            f"SSH={'allow' if self._blk7_cfg.allow_ssh_inbound else 'deny'} "
            f"IDS={self._blk7_cfg.ids_mode} "
            f"Snort={self._blk7_cfg.ids_snort_profile}"
        )
