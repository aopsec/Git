from __future__ import annotations

import re

CYBER_KEYWORDS: tuple[str, ...] = (
    "security", "seguranca", "segurança", "cyber", "ciber", "pentest",
    "bug bounty", "red team", "blue team", "vulnerability", "vulnerab",
    "exploit", "owasp", "mitre", "attack", "linux", "bash", "python",
    "docker", "vpn", "wireguard", "tor", "firewall", "ids", "ips",
    "suricata", "zeek", "falco", "auditd", "nftables", "fail2ban",
    "lynis", "rkhunter", "monit", "cve", "api", "graphql", "xss",
    "csrf", "ssrf", "sqli", "recon", "osint", "hardening",
)
STRONG_CYBER_KEYWORDS: tuple[str, ...] = (
    "cybersecurity", "cyber security", "information security", "web security",
    "network security", "penetration testing", "pentest", "bug bounty",
    "hacker", "hacking", "red team", "blue team", "vulnerability",
    "exploit", "owasp", "mitre", "cve", "nmap", "burp", "metasploit",
    "kali", "xss", "csrf", "ssrf", "sqli", "recon", "osint", "hardening",
    "suricata", "zeek", "falco", "auditd", "nftables", "fail2ban",
    "lynis", "rkhunter", "wireguard", "tor", "dnscrypt", "semgrep",
    "gitleaks", "vulnerabilidades", "cibersegurança", "segurança ofensiva",
)
NON_CYBER_MARKERS: tuple[str, ...] = (
    "matematic", "matemática", "discreta", "fundamentos", "cap01",
    "cap04", "cap07", "cap2", "reforço", "sistematizacao",
    "sistematização", "anexo", "cronograma", "benefícios", "beneficios",
    "comprovante", "boleto", "vagas geral", "desafio inicial",
    "codigo do despertar", "codigododespertar", "canais fornecidos",
    "ederhiedeki",
)
HARD_NON_CYBER_MARKERS: tuple[str, ...] = NON_CYBER_MARKERS
# [REF-CYBERPDF-05] Broad B00Ks discovery includes mixed personal-library shelves.
# Keep these shelves out of active CyberRef indexes unless they are curated explicitly.
NON_CYBER_PATH_PARTS: frozenset[str] = frozenset(
    {"1sem", "finance books", "learn programming", "self help books"}
)
CYBER_TITLE_MARKERS: tuple[str, ...] = (
    "advanced penetration testing", "api security", "black hat",
    "black-hat", "blue team", "bug bounty", "bug hunter", "cyber",
    "cve", "exploit", "forensic", "forensics", "graphql", "hacker",
    "hacking", "malicious code", "metasploit", "offensive security",
    "owasp", "penetration testing", "pentest", "privilege escalation",
    "red team", "reverse engineering", "security testing", "web hacking",
    "web penetration",
)
GENERAL_PROGRAMMING_TITLE_MARKERS: tuple[str, ...] = (
    "automate the boring stuff with python",
    "beyond the basic stuff with python",
    "build an html5 game",
    "how linux works",
    "learn windows powershell in a month of lunches",
    "learning python network programming",
    "make python talk",
    "no starch press the rust",
    "perl one liners",
    "powershell for sysadmins",
    "python 2 1 bible",
    "python pocket reference",
    "ruby by example",
    "the book of ruby",
    "the linux command line",
    "webbots spiders and screen scrapers",
    "wicked cool perl scripts",
    "wicked cool ruby scripts",
    "wicked cool shell scripts",
)
TOOL_NAMES: tuple[str, ...] = (
    "nmap", "burp", "metasploit", "kali", "docker", "linux", "bash",
    "python", "ffuf", "feroxbuster", "dirsearch", "arjun", "httpx",
    "katana", "nuclei", "suricata", "zeek", "falco", "auditd",
    "wireguard", "tor", "dnscrypt-proxy", "pi-hole", "pihole",
    "lynis", "rkhunter", "fail2ban", "monit", "netdata", "ntfy",
    "caddy", "semgrep", "gitleaks", "obsidian", "claude", "codex",
)
EXCLUDED_PARTS: frozenset[str] = frozenset(
    {".cache", ".cargo", ".git", ".venv", "__pycache__", "node_modules"}
)
EXCLUDED_SUBPATHS: tuple[str, ...] = (
    "/go/pkg/mod/",
    "/.local/share/Trash/",
)
URL_RE = re.compile(r"https?://[^\s)>\]\"']+")
COMMAND_RE = re.compile(
    r"^\s*(?:\$|#)?\s*(?:sudo\s+)?(?:bash|python3?|pipx|pip|go|cargo|"
    r"docker|nmap|curl|wget|ssh|scp|git|systemctl|journalctl|nft|iptables|"
    r"lynis|rkhunter|ffuf|feroxbuster|dirsearch|arjun|httpx|katana|nuclei)\b.*"
)
CODE_RE = re.compile(
    r"^\s*(?:#!|def\s+\w+\(|class\s+\w+|func\s+\w+\(|package\s+\w+|"
    r"import\s+\w+|from\s+\w+|for\s+\w+\s+in\s+|while\s+|if\s+\[|"
    r"case\s+.*\sin\s*$|function\s+\w+|[a-zA-Z_][\w-]*\(\)\s*\{)"
)
TECHNIQUE_KEYWORDS: tuple[str, ...] = (
    "reconnaissance", "enumeration", "fuzz", "scan", "payload", "exploit",
    "bypass", "brute force", "privilege escalation", "reverse shell",
    "web shell", "lateral movement", "persistence", "exfiltration",
    "counter-forensics", "xss", "csrf", "ssrf", "sqli", "idor", "jwt",
    "oauth", "graphql", "api", "wordlist", "nuclei", "nmap", "burp",
)
