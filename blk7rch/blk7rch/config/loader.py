"""Config loader — read JSON config files and merge with CLI arguments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from blk7rch.config.defaults import defaults_for_profile
from blk7rch.config.schema import BLK7Config


def load_config(config_path: Path, creds_path: Path | None = None) -> BLK7Config:
    """Load a BLK7rch JSON config file into a :class:`BLK7Config`.

    Parameters
    ----------
    config_path:
        Path to a JSON file with BLK7Config fields.
    creds_path:
        Optional path to a separate credentials JSON file that may contain
        ``encryption_password``, ``user_password``, and ``root_password``.

    Returns
    -------
    BLK7Config
        Fully populated configuration instance.

    Raises
    ------
    FileNotFoundError
        If *config_path* does not exist.
    json.JSONDecodeError
        If either file contains invalid JSON.
    ValueError
        If the merged configuration fails validation.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open() as fh:
        data: dict[str, Any] = json.load(fh)

    if creds_path is not None:
        if not creds_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")
        with creds_path.open() as fh:
            creds: dict[str, Any] = json.load(fh)
        data.update(creds)

    # Fill in any missing fields from profile defaults
    profile = data.get("profile", "workstation")
    defaults = defaults_for_profile(profile)
    merged = {**defaults, **data}

    # Only pass known BLK7Config fields
    known = BLK7Config.__dataclass_fields__.keys()
    filtered = {k: v for k, v in merged.items() if k in known}

    return BLK7Config(**filtered)


def merge_cli_args(cfg: BLK7Config, args: argparse.Namespace) -> BLK7Config:
    """Override *cfg* fields with any non-None values from parsed CLI *args*.

    Parameters
    ----------
    cfg:
        Base configuration to update.
    args:
        Parsed ``argparse.Namespace``; only attributes that exist as
        :class:`BLK7Config` fields and are not ``None`` are applied.

    Returns
    -------
    BLK7Config
        A new configuration instance with CLI overrides applied.
    """
    import dataclasses

    overrides: dict[str, Any] = {}
    known = BLK7Config.__dataclass_fields__.keys()

    for key in known:
        cli_val = getattr(args, key, None)
        if cli_val is not None:
            overrides[key] = cli_val

    if overrides:
        current = dataclasses.asdict(cfg)
        current.update(overrides)
        return BLK7Config(**current)

    return cfg


def config_to_json(cfg: BLK7Config, *, include_passwords: bool = False) -> str:
    """Serialise *cfg* to a JSON string suitable for ``--config``.

    Parameters
    ----------
    cfg:
        Configuration instance to serialise.
    include_passwords:
        When *False* (default), password fields are omitted from the output.

    Returns
    -------
    str
        Pretty-printed JSON string.
    """
    import dataclasses

    data = dataclasses.asdict(cfg)

    if not include_passwords:
        for key in ("encryption_password", "user_password", "root_password"):
            data.pop(key, None)

    return json.dumps(data, indent=2)
