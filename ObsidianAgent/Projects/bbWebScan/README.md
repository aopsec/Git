# bbWebScan

Scope-aware bug bounty web recon orchestrator. Runs a pipeline of specialized tools (httpx, katana, scrapy, discovery, nuclei, and optionally amass, naabu, jwt_tool, sqlmap) with strict scope enforcement and built-in security hardening.

## Introduction

bbWebScan orchestrates web reconnaissance for authorized bug bounty programs and penetration tests. It:

- **Enforces scope** — refuses to run outside declared target scope via `allowed_hosts` and `denied_hosts` gates
- **Pipelines tools** — chains subdomain discovery → port scan → live host detection → crawling → fuzzing → injection testing → template matching
- **Hardens security** — masks secrets in logs/reports, supports env-var-only credentials in profiles, redacts command arguments before dry-run echo
- **Detects tech** — auto-suggests wordlists based on detected server stack (PHP, Node.js, ASP.NET, etc.)
- **Extracts wordlists** — builds personalized wordlists from discovered paths for more effective fuzzing
- **Gathers findings** — JSON + Markdown reports with severity filtering and run history

Designed for operational efficiency: one-off CLI scans, saved profiles, CI/CD integration, and an interactive Rich-backed menu for guided setup.

---

## Information

### Architecture

**Pipeline order** (each stage is optional, gated on tool availability and enabling flags):

1. **amass** — Subdomain enumeration (opt-in, passive/active/intel modes)
2. **naabu** — Port discovery (opt-in, top-100/top-1000/full modes)
3. **httpx** — Live host + title + status detection
4. **katana** — Web crawling
5. **scrapy** — Deep crawling + secret/credential pattern extraction (safe-default)
6. **discovery** — Directory/file fuzzing (ffuf, feroxbuster, dirsearch)
7. **kiterunner** — API route discovery (opt-in)
8. **params** — Parameter discovery (arjun)
9. **jwt_tool** — JWT token analysis (opt-in)
10. **sqlmap** — SQL injection testing (opt-in, smooth/aggressive modes)
11. **nuclei** — Vulnerability scanning (community + custom templates)

### Tool Set

**Safe mode defaults** (no authorization needed):
- httpx, katana, scrapy

**Aggressive mode defaults** (requires `--ack-authorized`):
- safe defaults + ffuf, feroxbuster, arjun, nuclei

**Optional tools** (require explicit flags):
- `--enumerate-subdomains` → amass
- `--port-scan` → naabu
- `--api-discovery` → kiterunner
- `--jwt-analysis` → jwt_tool
- `--sqlmap-mode smooth|aggressive` → sqlmap

### Scope Gate

bbWebScan refuses to run when:

- Mode is aggressive without `--ack-authorized`
- Targets span multiple hosts but `allowed_hosts` is empty
- Any target normalizes to a public suffix (e.g., `com`, `co.uk`)

The `denied_hosts` list always wins over `allowed_hosts`.

### File Layout

```
bbwebscan/                 Main package
├── cli.py               Entry point + subcommand dispatch
├── menu*.py             Interactive Rich menu system
├── config.py            Config building, tool resolution
├── pipeline.py          Stage orchestration
├── stages/              Per-tool executors (httpx, katana, nuclei, ...)
├── wordlist_*.py        [v0.5.7] Auto-suggest + supplement wordlist building
├── auth.py              Header/cookie/raw-request handling
├── targets.py           URL normalization + scope filtering
├── models.py            Pydantic dataclasses (RunConfig, Finding, etc.)
└── ...
profiles/                Saved YAML program profiles
runs/                    Per-run artifacts (UTC-named subdirs)
tests/                   pytest suite + fixtures
```

---

## Correct Usage

### Quick Start

```bash
cd Projects/bbWebScan
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev,cov]'           # Install + dev/test tooling

# Interactive menu
bbwebscan                             # Open Rich menu (no args)
bbwebscan menu                        # Explicit subcommand

# Smart-default scan (one host, safe mode, dry-run first)
bbwebscan example.com

# Full-featured scan
bbwebscan scan --target app.example.com --mode aggressive --ack-authorized \
  --tool-timeout 30 --rate 100 --output-dir ./my-run
```

### Subcommands

```text
bbwebscan {menu,scan,install,doctor,init,history,show,compare}

  menu       Open interactive menu (also the no-args default)
  scan       Run a recon scan
  install    Install missing tools via ~/bbScan_Installer.sh
  doctor     Inspect toolchain readiness
  init       Scaffold a program profile YAML
  history    List past runs newest-first
  show       Print a past run's summary.md
  compare    Diff findings between two runs
```

### Scan Flags

```text
Targets & Scope:
  --target HOST           One or more hosts (repeatable)
  --input FILE            Newline-delimited file of targets
  --profile FILE          YAML program profile (defines scope, auth)

Mode & Authorization:
  --mode {safe,aggressive}        Default: safe
  --ack-authorized                Required for aggressive, active amass, full port-scan, sqlmap aggressive

Auth:
  --header "Name: Value"          One-off HTTP header (repeatable)
  --cookie "name=value"           One-off cookie (repeatable)
  --raw-request FILE              Raw HTTP request body for ffuf/dirsearch

Discovery & Crawling:
  --enumerate-subdomains          Enable amass (passive by default)
  --amass-mode {passive,active,intel}
  --port-scan                     Enable naabu
  --port-scan-mode {top-100,top-1000,full}
  --port-scan-rate N              Packets/sec (default 1000)
  --api-discovery                 Enable kiterunner
  --scrapy-deep                   Extract secrets from crawled content
  --scrapy-js-render              JS rendering via scrapy-playwright

Fuzzing & Injection:
  --wordlist PATH                 Fuzzer wordlist (auto-suggested if omitted)
  --enable-tool TOOL              No longer used in menu; CLI still accepts it
  --disable-tool TOOL             Exclude specific tools
  --sqlmap-mode {off,smooth,aggressive}  SQL injection testing
  --sqlmap-timeout SECONDS        Per-URL timeout (default 600)
  --jwt-analysis                  Enable jwt_tool

Tuning:
  --threads N                     Thread pool size (default: tool-dependent)
  --rate N                        Requests/sec (default: tool-dependent)
  --tool-timeout SECONDS          Per-tool timeout (default 15)
  --cmd-timeout SECONDS           Wall-clock subprocess timeout (default 900)
  --max-attempts N                Retry attempts on transient failure (default 1)
  --backoff-s SECONDS             Retry backoff base (default 2.0)

Output & Filtering:
  --output-dir DIR                Artifacts directory (default: runs/<UTC>)
  --min-severity {info,low,medium,high,critical}  Filter findings (default: info)
  --dry-run                       Preview commands, skip execution
  --quiet, -q                     Suppress per-stage progress

Validation:
  --check-dns                     Validate target DNS resolution (non-fatal)
  --check-tools                   Inventory tools only, no scan
  --strict-identity               Fail if any tool fingerprint is suspect
```

### Installation for System-Wide Use

```bash
pipx install -e .
# Then: bbwebscan (works from anywhere)
# Update: pipx upgrade bbwebscan
```

Without pipx, `bbwebscan` is only available inside the activated venv.

### Running for CI/CD

```bash
# Check tool readiness
bbwebscan doctor                    # Exit 2 if any tool is missing

# Scan with severity gating
bbwebscan scan --target app.example.com --mode safe --output-dir ./results
echo $?                             # 0=ok, 2=preflight error, 3=findings found

# Severity threshold for CI failure
bbwebscan scan ... --min-severity high   # Only high/critical block the gate
```

Exit codes:
- `0` — No errors, no findings (or all below threshold)
- `2` — Preflight error (missing tool, wordlist, or invalid scope)
- `3` — Findings found at or above `--min-severity` threshold

---

## Tips & Cheats

### Auth in Profiles

Keep credentials out of version control by using environment variables:

```yaml
# profiles/acme.yaml
program_name: acme
seed_urls:
  - https://app.acme.com
allowed_hosts:
  - app.acme.com
  - api.acme.com

auth:
  headers:
    Authorization: "Bearer ${ACME_TOKEN}"
  cookies:
    session: "${ACME_SESSION}"
```

Before running:
```bash
export ACME_TOKEN=... ACME_SESSION=...
bbwebscan scan --profile profiles/acme.yaml
```

Missing env vars raise an actionable error; bbwebscan never silently substitutes empty strings.

Interpolation is scoped to `auth.headers` and `auth.cookies` only — paths like `wordlist:` pass through verbatim, so `${HOME}/wordlists/...` works.

### Wordlist Auto-Suggestion

**[v0.5.7]** When you don't specify `--wordlist` or leave it blank in the menu:
1. httpx results are parsed for Server / X-Powered-By / Set-Cookie headers
2. Tech stack is detected (PHP, Node.js, ASP.NET, etc.)
3. A matching wordlist is auto-suggested from available options
4. Fallback: the default wordlist if no tech is detected

### Personalized Wordlist Building

**[v0.5.7]** After crawling, unique path segments from discovered URLs are extracted and merged with the base wordlist:
1. katana + scrapy crawl discovers paths
2. Words are extracted (e.g., `/api/users` → `api`, `users`)
3. Supplement written to `runs/<UTC>/wordlist_supplement.txt`
4. Merged with base → `runs/<UTC>/wordlist_effective.txt`
5. This effective list is used for fuzzing

### Scan Templates (Interactive Menu)

**[v0.5.7]** When you run `bbwebscan` or `bbwebscan menu` and select "Custom Scan", you are offered 4 templates:

1. **Passive Recon** — safe mode, httpx+katana+scrapy only, dry-run by default
2. **Full Web Scan** — aggressive mode, all default tools, run immediately
3. **API Recon** — aggressive with kiterunner focus, ffuf/feroxbuster disabled
4. **Manual (Custom)** — blank slate, customize every field

Pick one to pre-fill your settings, then override any field as needed.

### Manual Scanning

For one-off scans, use the CLI directly:

```bash
bbwebscan scan example.com                                    # Quick scan
bbwebscan scan example.com --mode aggressive --ack-authorized # Full scan
bbwebscan scan example.com --dry-run                          # Preview only
```

### Saved Profiles

Create and reuse profiles:

```bash
bbwebscan init my-program --target app.example.com
# Scaffolds profiles/my-program.yaml

# Edit and add auth/denied hosts as needed
nano profiles/my-program.yaml

# Run against saved profile
bbwebscan scan --profile profiles/my-program.yaml --mode aggressive --ack-authorized
```

### Run History

List past runs:
```bash
bbwebscan history --limit 20           # 20 most recent runs

bbwebscan show 20260515T140000Z        # Print summary of run (UTC dir name)

bbwebscan compare run-A run-B          # Diff findings between two runs
```

### Dry-Run Before Execution

Always preview commands first:

```bash
bbwebscan scan example.com --dry-run   # Print commands, skip execution
# Review the logs in runs/<UTC>/logs/

bbwebscan menu                         # Custom scan → "Preview command" option
```

### Troubleshooting

```bash
# Check all tools are installed
bbwebscan doctor                       # Lists installed vs missing

# If a tool is missing
bbwebscan install                      # Runs the installer script

# Verbose output (per-stage progress)
bbwebscan scan ... --verbose

# Retry settings (adjust for flaky networks)
bbwebscan scan ... --max-attempts 3 --backoff-s 3.0

# Tool-specific timeouts (for slow targets)
bbwebscan scan ... --tool-timeout 60 --cmd-timeout 1800
```

### CI/CD Integration

```yaml
# Example GitHub Actions
- name: Run bbWebScan
  run: |
    bbwebscan doctor || exit 2
    bbwebscan scan --target ${{ env.TARGET }} \
      --mode safe \
      --output-dir ./results
    # Exit 3 if high/critical findings; 0 otherwise
```

---

## Release Notes

See `CHANGELOG.md` for the full release history and migration notes.

---

## License

See `NOTICE` for attribution and licensing.
