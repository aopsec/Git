import os
import re
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any, Literal, cast

import yaml

from bbwebscan.auth import merge_auth
from bbwebscan.models import ProgramProfile, RetryPolicy, RunConfig
from bbwebscan.targets import normalize_target

SAFE_DEFAULT_TOOLS: tuple[str, ...] = ("httpx", "katana", "scrapy")
AGGRESSIVE_DEFAULT_TOOLS: tuple[str, ...] = (
    "httpx",
    "katana",
    "scrapy",
    "ffuf",
    "feroxbuster",
    "arjun",
    "nuclei",
)
# [v0.5.0] amass and kiterunner are opt-in via dedicated flags (not via
# --enable-tool), so they're SUPPORTED but not part of the default toolsets.
# [v0.5.5] jwt_tool (--jwt-analysis) and sqlmap (--sqlmap-mode) follow the
# same opt-in pattern: SUPPORTED but never auto-enabled.
OPTIONAL_TOOLS: tuple[str, ...] = ("dirsearch", "amass", "kiterunner", "jwt_tool", "sqlmap")
SUPPORTED_TOOLS: tuple[str, ...] = (
    SAFE_DEFAULT_TOOLS
    + tuple(tool for tool in AGGRESSIVE_DEFAULT_TOOLS if tool not in SAFE_DEFAULT_TOOLS)
    + OPTIONAL_TOOLS
)


_ENV_RE: re.Pattern[str] = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _interpolate_env(value: object) -> object:
    """Recursively replace ${VAR} placeholders with os.environ values.

    [v0.4.3 Item 7] Used to keep credentials (cookies/tokens) out of profile
    YAMLs that may live in dotfiles repos. Missing vars raise an actionable
    ValueError naming the variable; we never silently substitute empty.
    """
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            resolved = os.environ.get(name)
            if resolved is None:
                raise ValueError(
                    f"Profile references unset env var ${{{name}}}; "
                    "export it or remove the reference."
                )
            return resolved
        return _ENV_RE.sub(replace, value)
    if isinstance(value, dict):
        return {key: _interpolate_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_interpolate_env(item) for item in value]
    return value


def load_profile(profile_path: str | None) -> ProgramProfile:
    if profile_path is None:
        return ProgramProfile()
    path = Path(profile_path).expanduser()
    if not path.is_file():
        # [FIX-BBW-05] Report a CLI-facing profile error instead of a raw traceback.
        raise ValueError(f"Profile not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    # [v0.4.3 Item 7] Interpolate only inside auth.headers / auth.cookies — not
    # the whole profile, so a wordlist path containing literal ${HOME} is left alone.
    auth = data.get("auth")
    if isinstance(auth, dict):
        for key in ("headers", "cookies"):
            if key in auth:
                auth[key] = _interpolate_env(auth[key])
    return ProgramProfile.model_validate(data)


def build_run_config(args: Namespace) -> RunConfig:
    profile = load_profile(args.profile)
    # [FIX-BBW-09] Smart default: when no profile and a single explicit target,
    # derive allowed_hosts from that target so safe scans run profile-less.
    if not profile.allowed_hosts and not args.profile and len(args.target) == 1:
        derived = normalize_target(args.target[0]).host
        profile = profile.model_copy(update={"allowed_hosts": [derived]})
    mode = args.mode or profile.mode_default
    if mode == "aggressive" and not args.ack_authorized:
        raise ValueError("Aggressive mode requires --ack-authorized")
    # [v0.5.0] amass active/intel modes make detectable DNS/zone queries;
    # gate behind --ack-authorized just like aggressive mode.
    amass_mode_raw = getattr(args, "amass_mode", "passive") or "passive"
    if amass_mode_raw not in ("passive", "active", "intel"):
        raise ValueError(f"Unsupported --amass-mode: {amass_mode_raw}")
    amass_mode_arg = cast(Literal["passive", "active", "intel"], amass_mode_raw)
    if amass_mode_arg != "passive" and not args.ack_authorized:
        raise ValueError(
            f"--amass-mode {amass_mode_arg} requires --ack-authorized "
            "(active/intel modes make detectable queries)"
        )
    if mode == "safe" and args.ack_authorized:
        # [FIX-BBW-H] --ack-authorized is meaningful only for aggressive mode;
        # warn instead of silently ignoring so operators don't think they enabled
        # something stronger than they did.
        print(
            "[bbwebscan] note: --ack-authorized has no effect in safe mode",
            file=sys.stderr,
        )
    enumerate_subdomains = getattr(args, "enumerate_subdomains", False)
    api_discovery = getattr(args, "api_discovery", False)
    scrapy_deep = getattr(args, "scrapy_deep", False)
    scrapy_max_depth = getattr(args, "scrapy_max_depth", 2)
    scrapy_js_render = getattr(args, "scrapy_js_render", False)
    jwt_analysis = getattr(args, "jwt_analysis", False)
    sqlmap_mode_raw = getattr(args, "sqlmap_mode", "off") or "off"
    if sqlmap_mode_raw not in ("off", "smooth", "aggressive"):
        raise ValueError(f"Unsupported --sqlmap-mode: {sqlmap_mode_raw}")
    sqlmap_mode_arg = cast(Literal["off", "smooth", "aggressive"], sqlmap_mode_raw)
    if sqlmap_mode_arg == "aggressive" and not args.ack_authorized:
        raise ValueError("--sqlmap-mode aggressive requires --ack-authorized (high target load)")
    sqlmap_timeout = getattr(args, "sqlmap_timeout", 600) or 600
    selected_tools = resolve_selected_tools(
        mode=mode,
        profile_tools=profile.enabled_tools,
        enable_tools=args.enable_tool,
        disable_tools=args.disable_tool,
    )
    selected_tools = add_opt_in_tools(
        selected_tools,
        enumerate_subdomains=enumerate_subdomains,
        api_discovery=api_discovery,
        jwt_analysis=jwt_analysis,
        sqlmap_mode=sqlmap_mode_arg,
        disable_tools=args.disable_tool,
    )
    target_inputs = list(profile.seed_urls)
    target_inputs.extend(args.target)
    output_dir = Path(args.output_dir) if args.output_dir else Path.cwd() / "runs" / args.run_label
    retry = RetryPolicy(
        max_attempts=args.max_attempts or profile.retry.max_attempts,
        backoff_s=args.backoff_s if args.backoff_s is not None else profile.retry.backoff_s,
        transient_exit_codes=profile.retry.transient_exit_codes,
    )
    return RunConfig(
        program_name=profile.program_name,
        seed_urls=list(profile.seed_urls),
        allowed_hosts=list(profile.allowed_hosts),
        denied_hosts=list(profile.denied_hosts),
        auth=merge_auth(profile.auth, args.header, args.cookie, args.raw_request),
        mode=mode,
        enabled_tools=selected_tools,
        wordlist=Path(args.wordlist) if args.wordlist else profile.wordlist,
        threads=args.threads or profile.threads,
        rate=args.rate or profile.rate,
        tool_timeout_s=args.tool_timeout or profile.tool_timeout_s,
        command_wall_clock_s=args.cmd_timeout or profile.command_wall_clock_s,
        retry=retry,
        output_dir=output_dir,
        target_inputs=target_inputs,
        input_file=Path(args.input) if args.input else None,
        check_tools=args.check_tools,
        dry_run=args.dry_run,
        ack_authorized=args.ack_authorized,
        verbose=not getattr(args, "quiet", False),
        strict_identity=getattr(args, "strict_identity", False),
        profile_tool_identity=dict(profile.tool_identity),
        min_severity=getattr(args, "severity", None) or "info",
        preflight_dns=getattr(args, "check_dns", False),
        enumerate_subdomains=enumerate_subdomains,
        api_discovery=api_discovery,
        amass_mode=amass_mode_arg,
        scrapy_deep=scrapy_deep,
        scrapy_max_depth=scrapy_max_depth,
        scrapy_js_render=scrapy_js_render,
        jwt_analysis=jwt_analysis,
        sqlmap_mode=sqlmap_mode_arg,
        sqlmap_timeout=sqlmap_timeout,
        discovery_status_filter=list(profile.discovery_status_filter),
        nuclei_max_targets=profile.nuclei_max_targets,
    )


def resolve_selected_tools(
    mode: str,
    profile_tools: list[str],
    enable_tools: list[str],
    disable_tools: list[str],
) -> list[str]:
    defaults = list(AGGRESSIVE_DEFAULT_TOOLS if mode == "aggressive" else SAFE_DEFAULT_TOOLS)
    selected = set(defaults)
    selected.update(profile_tools)
    selected.update(enable_tools)
    selected.difference_update(disable_tools)
    unsupported = sorted(tool for tool in selected if tool not in SUPPORTED_TOOLS)
    if unsupported:
        raise ValueError(f"Unsupported tools selected: {', '.join(unsupported)}")
    return [tool for tool in SUPPORTED_TOOLS if tool in selected]


def add_opt_in_tools(  # noqa: PLR0913 - opt-in flags accumulate naturally; binding into a struct adds noise.
    selected_tools: list[str],
    *,
    enumerate_subdomains: bool,
    api_discovery: bool,
    jwt_analysis: bool,
    sqlmap_mode: str,
    disable_tools: list[str],
) -> list[str]:
    # [FIX-BBW-10] Flag-driven stages are real execution stages, so they must
    # appear in the same effective tool set used by inventory and preflight.
    selected = set(selected_tools)
    disabled = set(disable_tools)
    if enumerate_subdomains:
        if "amass" in disabled:
            raise ValueError("--enumerate-subdomains requires amass; remove --disable-tool amass")
        selected.add("amass")
    if api_discovery:
        if "kiterunner" in disabled:
            raise ValueError(
                "--api-discovery requires kiterunner; remove --disable-tool kiterunner"
            )
        selected.add("kiterunner")
    if jwt_analysis:
        if "jwt_tool" in disabled:
            raise ValueError("--jwt-analysis requires jwt_tool; remove --disable-tool jwt_tool")
        selected.add("jwt_tool")
    if sqlmap_mode != "off":
        if "sqlmap" in disabled:
            raise ValueError(
                f"--sqlmap-mode {sqlmap_mode} requires sqlmap; "
                "remove --disable-tool sqlmap"
            )
        selected.add("sqlmap")
    return [tool for tool in SUPPORTED_TOOLS if tool in selected]


REDACTED_PLACEHOLDER: str = "<redacted>"


def config_to_dict(config: RunConfig) -> dict[str, Any]:
    """Serialise RunConfig for `runs/<UTC>/run_config.json`.

    [v0.4.4] auth.headers and auth.cookies are redacted to keep resolved
    credentials off disk. Header/cookie KEYS are preserved so the audit
    trail still records which credentials were configured for the run.
    """
    payload = config.model_dump(mode="json")
    auth = payload.get("auth")
    if isinstance(auth, dict):
        for field in ("headers", "cookies"):
            values = auth.get(field)
            if isinstance(values, dict):
                auth[field] = {key: REDACTED_PLACEHOLDER for key in values}
    return payload
