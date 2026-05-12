from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from bbwebscan.menu_prompts import collect_env_refs, prompt, prompt_bool
from bbwebscan.menu_types import InputFunc, MenuIO, ScanSettings
from bbwebscan.models import AuthConfig, ProgramProfile
from bbwebscan.targets import normalize_target


@dataclass
class ProfileSaveOptions:
    program_name: str | None = None
    force: bool = False
    profile_headers: dict[str, str] | None = None
    profile_cookies: dict[str, str] | None = None


@dataclass
class ProfileAuthRefs:
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)


@dataclass
class ProfileScope:
    seed_urls: list[str] = field(default_factory=list)
    allowed_hosts: list[str] = field(default_factory=list)


def save_profile_interactive(
    settings: ScanSettings,
    io: MenuIO,
    *,
    input_func: InputFunc,
) -> Path:
    program = prompt("Program name", default_program_name(settings), input_func)
    out_default = f"profiles/{program}.yaml"
    out = Path(prompt("Profile output path", out_default, input_func)).expanduser()
    force = prompt_bool("Overwrite if profile exists", False, input_func)
    io.print("Saved profile auth values must reference env vars, for example Bearer ${BBW_TOKEN}.")
    io.print("Raw request file paths are one-off run inputs and are not saved to profiles.")
    headers = collect_env_refs("saved header", input_func)
    cookies = collect_env_refs("saved cookie", input_func)
    return save_profile(
        settings,
        out,
        options=ProfileSaveOptions(
            program_name=program,
            force=force,
            profile_headers=headers,
            profile_cookies=cookies,
        ),
    )


def save_profile(
    settings: ScanSettings,
    out: Path,
    *,
    options: ProfileSaveOptions | None = None,
) -> Path:
    """[MENU-SEC-051] Save only env-var auth references, never one-off secrets."""
    save_options = options or ProfileSaveOptions()
    if out.exists() and not save_options.force:
        raise FileExistsError(f"refusing to overwrite {out} (use overwrite in the menu)")
    auth = ProfileAuthRefs(
        headers=_selected_auth(save_options.profile_headers, settings.profile_auth_headers),
        cookies=_selected_auth(save_options.profile_cookies, settings.profile_auth_cookies),
    )
    require_env_refs(auth.headers, "header")
    require_env_refs(auth.cookies, "cookie")
    profile = _build_profile(
        settings,
        save_options.program_name,
        auth,
        profile_scope_from_targets(settings.targets),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(profile.model_dump(mode="json"), sort_keys=True)
    out.write_text(body, encoding="utf-8")
    return out


def require_env_refs(values: dict[str, str], kind: str) -> None:
    bad = [name for name, value in values.items() if "${" not in value or "}" not in value]
    if bad:
        raise ValueError(
            f"saved profile {kind} values must use env-var references: {', '.join(bad)}"
        )


def profile_scope_from_targets(targets: list[str]) -> ProfileScope:
    normalized = [normalize_target(target) for target in targets]
    seed_urls = [target.seed_url for target in normalized]
    allowed_hosts = sorted({target.host for target in normalized})
    return ProfileScope(seed_urls=seed_urls, allowed_hosts=allowed_hosts)


def default_program_name(settings: ScanSettings) -> str:
    if settings.profile:
        return Path(settings.profile).stem
    if settings.targets:
        return normalize_target(settings.targets[0]).host.replace(".", "-")
    return "ad-hoc"


def _selected_auth(
    explicit: dict[str, str] | None,
    stored: dict[str, str],
) -> dict[str, str]:
    return dict(explicit if explicit is not None else stored)


def _build_profile(
    settings: ScanSettings,
    program_name: str | None,
    auth: ProfileAuthRefs,
    scope: ProfileScope,
) -> ProgramProfile:
    defaults = ProgramProfile()
    profile = ProgramProfile(
        program_name=program_name or default_program_name(settings),
        seed_urls=scope.seed_urls,
        allowed_hosts=scope.allowed_hosts,
        auth=AuthConfig(
            headers=auth.headers,
            cookies=auth.cookies,
            raw_request=None,
        ),
        mode_default=settings.mode,
        enabled_tools=list(dict.fromkeys(settings.enable_tool)),
        threads=settings.threads or defaults.threads,
        rate=settings.rate or defaults.rate,
        tool_timeout_s=settings.tool_timeout or defaults.tool_timeout_s,
        command_wall_clock_s=settings.cmd_timeout or defaults.command_wall_clock_s,
    )
    if settings.wordlist:
        return profile.model_copy(update={"wordlist": Path(settings.wordlist)})
    return profile
