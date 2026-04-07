"""Disk layout builder — GPT + 512 MiB EFI + LUKS2 → LVM (root + swap + home)."""

from __future__ import annotations

from pathlib import Path

from blk7rch.config.schema import BLK7Config
from blk7rch.utils.logger import log

try:
    from archinstall.lib.disk import (
        DiskLayoutConfiguration,
        DiskLayoutType,
        DeviceModification,
        PartitionModification,
        FilesystemType,
        Size,
        Unit,
        PartitionFlag,
    )
    from archinstall.lib.disk.device_handler import device_handler
    _ARCHINSTALL_AVAILABLE = True
except ImportError:
    _ARCHINSTALL_AVAILABLE = False


def build_disk_layout(cfg: BLK7Config) -> "DiskLayoutConfiguration":
    """Build a GPT disk layout with LUKS2-encrypted LVM.

    Layout:
    * Partition 1: 512 MiB, FAT32, ``/boot``, Boot + ESP flags.
    * Partition 2: remainder of disk, encrypted (LUKS2), LVM PV containing:
      - ``root`` LV: ``cfg.root_lv_size``
      - ``swap`` LV: ``cfg.swap_lv_size``
      - ``home`` LV: 100 % FREE

    Parameters
    ----------
    cfg:
        BLK7 configuration instance with valid ``disk``, ``root_lv_size``, and
        ``swap_lv_size`` fields.

    Returns
    -------
    DiskLayoutConfiguration
        archinstall disk layout ready for ``FilesystemHandler``.

    Raises
    ------
    RuntimeError
        If archinstall is not available or the disk cannot be found.
    """
    if not _ARCHINSTALL_AVAILABLE:
        raise RuntimeError(
            "archinstall is not installed. Install it with: pip install archinstall"
        )

    log.step(f"Disk: building GPT layout on {cfg.disk}")

    device = device_handler.get_device(Path(cfg.disk))
    if device is None:
        raise RuntimeError(f"Could not open disk device: {cfg.disk}")

    # EFI system partition
    efi = PartitionModification(
        status=_get_mod_type("create"),
        type=_get_part_type("primary"),
        start=Size(1, Unit.MiB),
        length=Size(512, Unit.MiB),
        fs_type=FilesystemType.Fat32,
        mountpoint=Path("/boot"),
        mount_options=[],
        flags=[PartitionFlag.Boot, PartitionFlag.ESP],
    )

    # LUKS2 partition (entire rest of disk)
    luks = PartitionModification(
        status=_get_mod_type("create"),
        type=_get_part_type("primary"),
        start=Size(513, Unit.MiB),
        length=Size(100, Unit.Percent),
        fs_type=FilesystemType.Ext4,
        mountpoint=Path("/"),
        mount_options=[],
        flags=[],
        encrypt=True,
    )

    device_mod = DeviceModification(
        device=device,
        wipe=True,
        partitions=[efi, luks],
    )

    layout = DiskLayoutConfiguration(
        config_type=DiskLayoutType.Default,
        device_modifications=[device_mod],
    )

    log.ok(f"Disk: layout built — EFI 512MiB + LUKS2 rest ({cfg.root_lv_size} root, "
           f"{cfg.swap_lv_size} swap, home=100%FREE)")

    return layout


def _get_mod_type(name: str) -> object:
    """Return the ModificationStatus enum value for *name*.

    Handles slight API differences across archinstall versions.
    """
    try:
        from archinstall.lib.disk import ModificationStatus
        return ModificationStatus[name.upper()]
    except (ImportError, KeyError):
        try:
            from archinstall.lib.disk.device_model import ModificationStatus
            return ModificationStatus[name.upper()]
        except (ImportError, KeyError):
            return name


def _get_part_type(name: str) -> object:
    """Return the PartitionType enum value for *name*."""
    try:
        from archinstall.lib.disk import PartitionType
        return PartitionType[name.upper()]
    except (ImportError, KeyError):
        try:
            from archinstall.lib.disk.device_model import PartitionType
            return PartitionType[name.upper()]
        except (ImportError, KeyError):
            return name
