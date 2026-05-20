import argparse
from pathlib import Path

import yaml

from bbwebscan.models import ProgramProfile
from bbwebscan.targets import normalize_target

# [FIX-BBW-I] yaml.safe_dump strips comments, so we append guidance after the
# dump. yaml.safe_load on read still ignores these lines, so the file remains
# round-trippable through ProgramProfile.model_validate.
GUIDANCE_HINT: str = """
# tip: enabled_tools is empty so safe-mode defaults (httpx, katana) apply.
# to run aggressive recon, set:
#   enabled_tools: [ffuf, feroxbuster, arjun, nuclei]
# and pass `--mode aggressive --ack-authorized` to bbwebscan scan.
"""


def scaffold_profile(
    program_name: str,
    targets: list[str],
    out: Path,
    *,
    force: bool = False,
) -> Path:
    if out.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {out} (use --force)")
    if not targets:
        raise ValueError("at least one --target is required")
    seed_urls = [t if "://" in t else f"https://{t}" for t in targets]
    allowed_hosts = sorted({normalize_target(t).host for t in targets})
    profile = ProgramProfile(
        program_name=program_name,
        seed_urls=seed_urls,
        allowed_hosts=allowed_hosts,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = profile.model_dump(mode="json")
    body = yaml.safe_dump(payload, sort_keys=True)
    out.write_text(body + GUIDANCE_HINT, encoding="utf-8")
    return out


def run_init(args: argparse.Namespace) -> int:
    targets = list(args.target)
    out = (
        Path(args.out).expanduser()
        if args.out
        else Path("profiles") / f"{args.program_name}.yaml"
    )
    written = scaffold_profile(args.program_name, targets, out, force=args.force)
    print(f"wrote {written}", flush=True)
    return 0
