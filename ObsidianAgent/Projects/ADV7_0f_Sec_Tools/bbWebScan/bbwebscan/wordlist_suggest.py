import re
from pathlib import Path

TECH_WORDLIST_MAP: dict[str, Path] = {
    "php": Path("/home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-quick.txt"),
    "nodejs": Path("/home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-quick.txt"),
    "aspnet": Path("/home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-quick.txt"),
    "java": Path("/home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-master.txt"),
    "python": Path("/home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-master.txt"),
}


def detect_tech(httpx_stdout_path: Path) -> str | None:
    """Detect server technology from httpx response headers.

    Scans for Server, X-Powered-By, and Set-Cookie patterns to fingerprint
    the target stack (php, nodejs, aspnet, java, python).
    Returns the detected tech or None if no signature matches.
    """
    if not httpx_stdout_path.is_file():
        return None

    try:
        content = httpx_stdout_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, ValueError):
        return None

    # Fingerprints: lower-case tech name → list of patterns
    fingerprints = {
        "php": [
            r"X-Powered-By: PHP",
            r"Server: .*PHP",
            r"PHPSESSID",
        ],
        "nodejs": [
            r"X-Powered-By: Express",
            r"X-Powered-By: Node\.js",
            r"Server: .*Node\.js",
            r"Server: .*Express",
        ],
        "aspnet": [
            r"X-Powered-By: ASP\.NET",
            r"X-AspNet",
            r"ASP\.NET_SessionId",
        ],
        "java": [
            r"Server: .*Tomcat",
            r"X-Powered-By: Java",
            r"JSESSIONID",
        ],
        "python": [
            r"Server: .*Python",
            r"X-Powered-By: Django",
            r"X-Powered-By: Flask",
        ],
    }

    for tech, patterns in fingerprints.items():
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return tech

    return None


def suggest_wordlist(run_dir: Path, fallback: Path) -> Path:
    """Suggest a wordlist based on detected tech, or return fallback.

    Reads httpx stdout logs from the run directory, detects technology,
    and returns the mapped wordlist. If no match, returns the fallback path.
    """
    httpx_log = run_dir / "logs" / "httpx.stdout.log"
    tech = detect_tech(httpx_log)

    if tech and tech in TECH_WORDLIST_MAP:
        suggested = TECH_WORDLIST_MAP[tech]
        if suggested.is_file():
            return suggested

    return fallback
