from __future__ import annotations

import argparse
from pathlib import Path

from bbwebscan.config import load_profile
from bbwebscan.init_profile import run_init
from bbwebscan.menu_prompts import confirm, prompt_bool
from bbwebscan.menu_types import InputFunc, MenuIO, default_input


def run_profiles_menu(io: MenuIO, *, input_func: InputFunc = default_input) -> int:
    """Manage profiles: list/create/load/delete."""
    while True:
        io.panel("Manage Profiles", _profiles_menu_body())
        choice_val = input_func("Choose [1-5]: ").strip()

        if choice_val == "1":
            _list_profiles(io)
        elif choice_val == "2":
            _create_profile(io, input_func)
        elif choice_val == "3":
            _load_and_describe_profile(io, input_func)
        elif choice_val == "4":
            _delete_profile(io, input_func)
        elif choice_val == "5":
            return 0
        else:
            io.print("Choose a number from 1 to 5.")


def _list_profiles(io: MenuIO) -> None:
    """List all profiles in profiles/ directory."""
    profiles_dir = Path("profiles")
    if not profiles_dir.exists():
        io.print("No profiles directory found.")
        return

    files = sorted(profiles_dir.glob("*.yaml"))
    if not files:
        io.print("No profiles found.")
        return

    io.print("\nAvailable profiles:")
    for f in files:
        io.print(f"  - {f.stem}")


def _create_profile(io: MenuIO, input_func: InputFunc) -> None:
    """Create a new profile using the init wizard."""
    program = input_func("Program name: ").strip()
    if not program:
        io.print("Profile creation cancelled.")
        return

    targets_raw = input_func("Targets (comma-separated): ").strip()
    targets = [t.strip() for t in targets_raw.split(",") if t.strip()]

    out_raw = input_func("Output profile path [profiles/<program>.yaml]: ").strip()
    out = out_raw or f"profiles/{program}.yaml"

    force = prompt_bool("Overwrite if exists", False, input_func)

    try:
        args = argparse.Namespace(
            program_name=program,
            target=targets,
            out=out,
            force=force,
            ack_authorized=False,
        )
        run_init(args)
        io.print(f"Profile saved to {out}")
    except FileExistsError as exc:
        io.print(f"[bbwebscan menu] {exc}")
    except ValueError as exc:
        io.print(f"[bbwebscan menu] {exc}")


def _load_and_describe_profile(io: MenuIO, input_func: InputFunc) -> None:
    """Load and display a profile's contents."""
    profiles_dir = Path("profiles")
    files = sorted(profiles_dir.glob("*.yaml")) if profiles_dir.exists() else []

    if not files:
        io.print("No profiles found.")
        return

    prompt_str = "Choose profile (" + "/".join(p.stem for p in files) + "): "
    chosen = input_func(prompt_str).strip()

    if not chosen:
        return

    profile_path = profiles_dir / f"{chosen}.yaml"
    if not profile_path.exists():
        io.print(f"Profile {chosen} not found.")
        return

    try:
        profile = load_profile(str(profile_path))
        rows = [
            ["Program", profile.program_name],
            ["Seed URLs", ", ".join(profile.seed_urls)],
            ["Allowed Hosts", ", ".join(profile.allowed_hosts)],
            ["Mode", profile.mode_default],
            ["Threads", str(profile.threads)],
            ["Rate", str(profile.rate)],
        ]
        io.table("Profile", ["Setting", "Value"], rows)
    except Exception as exc:
        io.print(f"[bbwebscan menu] {exc}")


def _delete_profile(io: MenuIO, input_func: InputFunc) -> None:
    """Delete a profile."""
    profiles_dir = Path("profiles")
    files = sorted(profiles_dir.glob("*.yaml")) if profiles_dir.exists() else []

    if not files:
        io.print("No profiles found.")
        return

    prompt_str = "Choose profile to delete (" + "/".join(p.stem for p in files) + "): "
    chosen = input_func(prompt_str).strip()

    if not chosen:
        return

    profile_path = profiles_dir / f"{chosen}.yaml"
    if not profile_path.exists():
        io.print(f"Profile {chosen} not found.")
        return

    if confirm(f"Delete {chosen}", input_func, default=False):
        try:
            profile_path.unlink()
            io.print(f"Deleted {chosen}.")
        except Exception as exc:
            io.print(f"[bbwebscan menu] {exc}")


def _profiles_menu_body() -> str:
    """Return the profiles submenu text."""
    return "\n".join((
        "1. List profiles",
        "2. Create profile",
        "3. Load and describe profile",
        "4. Delete profile",
        "5. Back to main menu",
    ))
