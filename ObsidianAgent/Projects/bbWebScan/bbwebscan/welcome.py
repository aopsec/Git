from bbwebscan import __version__
from bbwebscan.config import SUPPORTED_TOOLS
from bbwebscan.models import ToolStatus
from bbwebscan.preflight import inventory_tools

WELCOME_HEADER = f"bbWebScan v{__version__} — bug bounty web recon orchestrator"
QUICK_COMMANDS = (
    "  bbwebscan example.com           # safe scan against one host",
    "  bbwebscan scan --profile P      # full run with a YAML profile",
    "  bbwebscan install               # install missing recon tools",
    "  bbwebscan doctor                # toolchain readiness check",
    "  bbwebscan init <program>        # scaffold a program profile",
)


def build_panel(statuses: list[ToolStatus]) -> str:
    ready = sum(1 for s in statuses if s.found and s.identity != "suspect")
    lines = [
        WELCOME_HEADER,
        "",
        "Quick commands:",
        *QUICK_COMMANDS,
        "",
        f"Toolchain: {ready}/{len(statuses)} tools ready"
        " (run `bbwebscan doctor` for the full breakdown)",
    ]
    return "\n".join(lines)


def print_welcome() -> None:
    print(build_panel(inventory_tools(SUPPORTED_TOOLS)))
