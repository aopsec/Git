<!--
  ════════════════════════════════════════════════════════════════════════════
  ADV7SEC — CVE Vulnerability Assessment Report Template  v1.0
  Style  : Burp Suite Professional + HackerOne + Bugcrowd VRT
  Maintainer: ADVAN7 Offensive Security | https://github.com/aopsec
  ════════════════════════════════════════════════════════════════════════════

  PLACEHOLDER LEGEND
  ──────────────────
  {{AUTO:name}}  = Auto-filled by new_report.sh — do not edit by hand
  [DESCRIPTION]  = Required manual fill — replace with actual value
  <!-- OPT -->   = Optional section — include when evidence exists, omit otherwise
  <!-- FILL -->  = Required section — do not leave with placeholder text in final report

  INSTANTIATION
  ─────────────
  Manual  : Copy this file, replace every [DESCRIPTION] and {{AUTO:*}} placeholder.
  Scripted: bash findings/templates/new_report.sh --cve CVE-XXXX-XXXXX \
                  --target https://target.com --severity CRITICAL --phase 8

  FINDING BLOCKS
  ──────────────
  Section §3 contains one finding block. Duplicate the block between
  ─── BEGIN FINDING ─── and ─── END FINDING ─── for each additional finding.
  Order by CVSS score descending (Critical → Info).
-->

---

**ADVAN7 Offensive Security** &nbsp;|&nbsp; `https://github.com/aopsec`  
**Classification:** `[TLP:WHITE / TLP:GREEN / TLP:AMBER / CONFIDENTIAL]`  
**Report ID:** `ADV7-{{AUTO:date_compact}}-001`  
**Template version:** `1.0`  
**Report date:** `{{AUTO:date}}`  
**Assessor:** `ADVAN7 Offensive Security`

---

# Vulnerability Assessment Report
## [ENGAGEMENT TITLE — e.g.: vswitcher.com Web Application Security Assessment]

---

## §0 — Authorization Declaration

> **THIS REPORT DOCUMENTS AUTHORIZED SECURITY TESTING ONLY.**
> Testing was conducted with explicit written permission for the defined scope below.

<!-- FILL -->

| Field | Value |
|---|---|
| Authorized target | `{{AUTO:target}}` |
| Host | `{{AUTO:host}}` |
| Authorization type | `[Bug Bounty Program / Penetration Test Agreement / CTF / Private Invite]` |
| Program / Client | `[HackerOne @program-slug / Company Name]` |
| Scope | `[In-scope domains and IP ranges as defined by program policy]` |
| Exclusions | `[Out-of-scope assets — e.g.: *.third-party-cdn.com, *.api-partner.io]` |
| Tester | `ADVAN7 Offensive Security` |
| Testing window | `{{AUTO:date}}` |

All findings are disclosed in accordance with the program's responsible disclosure policy.
No testing was performed outside the declared scope.

---

## §1 — Executive Summary

<!-- FILL: 2–3 sentences — what was tested, finding count, overall risk, top priority. -->

[A web application security assessment of `{{AUTO:host}}` was performed using
adv7FUZZ `{{AUTO:version}}` across [N] reconnaissance and vulnerability phases. The
assessment identified [N] findings: [N] Critical, [N] High, [N] Medium, [N] Low, and
[N] Informational. Immediate remediation priority should be given to [FINDING IDs].]

### Severity Distribution

| Critical | High | Medium | Low | Info | False Positive |
|:---:|:---:|:---:|:---:|:---:|:---:|
| [N] | [N] | [N] | [N] | [N] | [N] |

**Overall Risk Rating:** `[CRITICAL / HIGH / MEDIUM / LOW]`

---

## §2 — Methodology

| Field | Value |
|---|---|
| Primary scanner | `adv7FUZZ {{AUTO:version}}` |
| Scan directory | `{{AUTO:scandir}}` |
| Phases executed | `{{AUTO:phase}}` |
| Egress mode | `[Tor via torsocks / Direct / Burp proxy at 127.0.0.1:[PORT]]` |
| Wordlists | `SecLists: common.txt, big.txt, combined_words.txt, api/objects.txt` |
| Extensions scanned | `.php,.html,.txt,.bak,.zip,.sql,.conf,.old,.jar,.json,.xml,.env,.log` |
| Nuclei tags | `[cve,misconfig,exposure,tech,api]` |
| OOB server | `[interactsh OAST host / N/A — OOB not used]` |
| Scan date | `{{AUTO:date}}` |
| Tester environment | `[Arch Linux x86_64 / Kali 2024.x / ...]` |

<!-- OPT: methodology notes -->
> **Tor egress note:** When Tor was used as egress, time-based nuclei findings
> (duration-threshold templates) require independent OOB validation to rule out
> Tor RTT false positives (~7–9s baseline). See individual finding Validation Status tables.

---

## §3 — Findings

<!--
  ─── BEGIN FINDING ──────────────────────────────────────────────────────────
  Copy this entire block (from BEGIN to END) for each additional finding.
  Replace {{AUTO:*}} and [PLACEHOLDER] with actual values.
  ──────────────────────────────────────────────────────────────────────────── -->

---

## [CRITICAL] F-01 — {{AUTO:cve}}

> **Severity:** `{{AUTO:severity}}` &nbsp;|&nbsp;
> **CVSS v3.1:** `[0.0]` &nbsp;|&nbsp;
> **Confidence:** `[Certain / Firm / Tentative]` &nbsp;|&nbsp;
> **Status:** `[Confirmed / False Positive / Needs Validation]`

### Classification

<!-- FILL -->

| Field | Value |
|---|---|
| CVE ID | `{{AUTO:cve}}` |
| CVSS v3.1 Score | `[0.0]` |
| CVSS v3.1 Vector | `CVSS:3.1/AV:[N∣A∣L∣P]/AC:[L∣H]/PR:[N∣L∣H]/UI:[N∣R]/S:[U∣C]/C:[N∣L∣H]/I:[N∣L∣H]/A:[N∣L∣H]` |
| Severity | `{{AUTO:severity}}` |
| Confidence | `[Certain — OOB confirmed / Firm — strong indicator / Tentative — tool-only]` |
| CWE | `[CWE-NNN: Vulnerability Name]` |
| VRT Category | `[e.g.: Server-Side Injection > SQL Injection > Error-based]` |
| OWASP Category | `[e.g.: A03:2021 – Injection]` |
| Status | `[Confirmed / Confirmed False Positive / Needs Manual Validation]` |

### Target

<!-- FILL -->

| Field | Value |
|---|---|
| Host | `{{AUTO:target}}` |
| Vulnerable path | `[/path/to/endpoint]` |
| HTTP method | `[GET / POST / PUT / DELETE / PATCH]` |
| Authentication | `[None required / Session token / API key / Admin only]` |
| Parameter / Field | `[parameter name, JSON key, HTTP header, or N/A]` |
| Affected software | `[Application name + version — e.g.: MagnusBilling 7.1.8]` |
| Technology stack | `[PHP 7.3.33 / Django 4.1 / Express 4.18 / Apache 2.4.51]` |

---

### Issue Background

<!-- Burp Suite Pro style — generic CLASS description.
     NOT instance-specific. Explain what this vulnerability TYPE is,
     how it works mechanically, and why it is dangerous in general.
     A reader with no prior context should understand the class before seeing evidence. -->

<!-- FILL -->

[Vulnerability class explanation. Write 2–4 paragraphs covering:
1. What the vulnerability is (mechanism)
2. How it is exploited generically
3. What an attacker can achieve with it
4. Why it persists (common root causes)

Example for OS Command Injection / RCE:
"Command injection occurs when user-supplied data is incorporated into an OS-level
command without adequate sanitization or escaping. Affected applications typically
pass user input to PHP functions such as `exec()`, `passthru()`, `system()`, or
`shell_exec()`, or use string concatenation to build shell commands. An attacker who
can influence these inputs can append shell metacharacters (`;`, `|`, `&&`, backticks)
to terminate the intended command and inject arbitrary commands.

Successful exploitation executes in the security context of the web server process
(commonly `www-data`, `apache`, or `nobody`). From this position, an attacker can
enumerate the filesystem, extract credentials, install persistent backdoors, pivot to
internal network segments, or exfiltrate database contents. When the server process
runs with elevated privileges the blast radius extends to full system compromise.

Root causes include: direct use of shell functions with unsanitized input, over-reliance
on client-side validation, insufficient server-side input filtering, and legacy code
that predates modern security-aware frameworks."]

---

### Issue Detail

<!-- Instance-specific evidence. What is SPECIFICALLY wrong on THIS target.
     Reference: exact endpoint, observed server behavior, version fingerprint,
     configuration detail, response headers. Do NOT repeat generic class explanation. -->

<!-- FILL -->

[Specific to this target. Example:
"`{{AUTO:host}}` exposes [Application Name] version [X.Y.Z] at `[/path/]`. The
vulnerable endpoint `[/path/endpoint?param=VALUE]` passes the `[param]` parameter
directly to `[function/syscall]` without sanitization. The PHP runtime is `PHP/7.3.33`
(confirmed via `X-Powered-By` response header on `{{AUTO:target}}`). The server is
fronted by Cloudflare, but origin IP `[X.X.X.X]` is reachable directly, bypassing WAF
filtering. [Describe any authentication/authorization context.]"]

---

### Proof of Concept

#### Discovery

<!-- FILL -->

- **Phase:** `{{AUTO:phase}}` — `[Phase name]`
- **Detection method:** `[nuclei template / manual request / adv7FUZZ auto-calibration hit]`
- **Nuclei template / rule:** `[template path — e.g.: http/cves/2023/CVE-2023-30258.yaml]`
- **Scanner version:** `adv7FUZZ {{AUTO:version}}`
- **Scan run directory:** `{{AUTO:scandir}}`
- **Initial indicator:** `[HTTP status, response time, OOB callback, body snippet]`

#### Reproduction Steps

<!-- FILL — numbered, fully deterministic, reproducible from a fresh session.
     A reader with the described tool set must be able to reproduce with no ambiguity. -->

1. `[Precondition: tool/auth/network setup — e.g.: Start interactsh-client to capture OOB]`
2. `[Send the triggering request to the specific URL]`
3. `[Supply the payload — include exact payload string]`
4. `[Observe the indicator — specific HTTP code, timing, OOB host callback, body content]`

#### Evidence

<!-- FILL: minimal reproducer — curl command + annotated response -->

```bash
# Minimal reproducer
curl -sk -X [METHOD] '{{AUTO:target}}/[path]' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0' \
  [additional headers / -d 'body'] \
  -w "\n---\nHTTP:%{http_code} | Time:%.3{time_total}s | Size:%{size_download}b\n"

# Expected vulnerable response:
# HTTP:[code] | Time:[Xs] | [Observable indicator — e.g.: command output, OOB callback]
```

<!-- OPT: full HTTP request/response (Burp Suite raw format) -->

```http
[METHOD] [PATH] HTTP/1.1
Host: {{AUTO:host}}
User-Agent: [UA string]
[Content-Type: application/x-www-form-urlencoded]

[request body if POST — include full payload]
```

```http
HTTP/1.1 [STATUS] [Reason]
Server: [server header]
Content-Type: [type]
[X-Powered-By: ...]

[Response body — truncate to relevant section, mark truncation with ...]
```

<!-- OPT: OOB callback log -->
```
# interactsh-client log (if OOB fired):
[TIMESTAMP] [OAST host] — [protocol] interaction from [attacker IP]
DNS query from [server IP] → confirmed out-of-band callback
```

---

### Impact

<!-- HackerOne style — business/user impact.
     Answer: WHO is affected, WHAT can attacker do, WHAT data at risk,
     IS user interaction required, WHAT is the blast radius. -->

<!-- FILL -->

[Impact statement. Be concrete and factual — no speculation.

Example: "A remote, unauthenticated attacker who can send HTTP requests to
`{{AUTO:target}}` can execute arbitrary OS-level commands as the `[process user]`
web server process. This enables:
- Full read/write access to the application database, including [data types: credentials, PII, billing records]
- Installation of a persistent reverse shell or webshell
- Lateral movement to [internal network segments accessible from the server]
- Credential extraction from `/etc/passwd`, application config files, and database connection strings

Estimated affected user population: [N users / all registered accounts / unknown].
No user interaction or authentication is required to exploit this vulnerability.
Cloudflare WAF provides partial mitigation but is bypassable via direct origin IP access."]

**CVSS v3.1 Impact Breakdown:**

| Metric | Value | Justification |
|---|---|---|
| Confidentiality | `[High / Low / None]` | `[e.g.: full DB access — all user data readable]` |
| Integrity | `[High / Low / None]` | `[e.g.: arbitrary file write — data can be modified]` |
| Availability | `[High / Low / None]` | `[e.g.: process termination — service disruption possible]` |
| Scope | `[Unchanged / Changed]` | `[e.g.: Changed — attacker gains access beyond web process]` |

---

### Remediation Background

<!-- Burp Suite Pro style — generic fix guidance for this vulnerability CLASS.
     NOT instance-specific. What developers must understand to fix this class correctly. -->

<!-- FILL -->

[Generic remediation guidance. 2–3 paragraphs.

Example for command injection:
"The most effective mitigation is to avoid invoking shell commands with user-supplied
input entirely. Where system-level calls are unavoidable, use language-native
parameterized APIs that prevent shell interpretation — for example, Python's
`subprocess.run([cmd, arg1, arg2])` (array form) rather than `subprocess.run(cmd, shell=True)`,
or PHP's `escapeshellarg()` / `escapeshellcmd()` as a secondary defense.

Allowlist validation of inputs before any processing is a strong defense-in-depth layer:
define the set of permitted values and reject everything outside that set. Deny-list
approaches (filtering known-bad characters) are insufficient — encoding variants and
context-specific bypasses make them reliably bypassable.

WAF rules provide defense-in-depth but must not be the primary control. A web application
firewall can be bypassed via origin IP access, protocol quirks, or payload obfuscation,
and provides no protection against authenticated insider misuse."]

---

### Remediation Detail

<!-- Specific fix for THIS instance — exact version, config change, code diff. -->

<!-- FILL -->

**Immediate action (apply first):**

> `[Exact version to upgrade to / WAF rule / config key to change — e.g.: "Upgrade MagnusBilling to ≥ 7.1.9 (commit ccff9f6 addresses CVE-2023-30258)"]`

**Code-level fix:**

```[language]
// ✗ VULNERABLE
[vulnerable code snippet — exact, not paraphrased]

// ✓ FIXED
[fixed code snippet — minimal diff, same context]
```

**Defense-in-depth hardening:**
- `[Additional control 1 — e.g.: WAF rule blocking */mbilling/lib/icepay/* path pattern]`
- `[Additional control 2 — e.g.: Disable PHP functions: exec, system, passthru in php.ini]`
- `[Additional control 3 — e.g.: Run web server process as non-privileged dedicated user]`

**Estimated remediation effort:** `[< 1 hour — patch only / 1 day — code change / 1 week — architectural change]`

---

### Validation Status

<!-- FILL -->

| Vector | Result |
|---|---|
| OOB (OAST) | `[Fired at [TIMESTAMP] from [server IP] / No callback after [X] minutes / Not tested]` |
| Time-based | `[Measured [X]ms — threshold [Y]ms — [Exceeds / Below threshold] / N/A]` |
| Manual curl | `[Confirmed: [specific indicator observed] / Not confirmed / N/A]` |
| Nuclei template | `[nuclei v[X.Y.Z] — [template name] — [hit/miss]]` |
| False positive factors | `[None / Tor RTT ~[X]s inflated timing / PATH_INFO routing / other]` |
| Tor egress effect | `[Not used / Used — adds [X-Y]s RTT — time-based findings require OOB confirm]` |
| Validation confidence | `[Certain — OOB + manual / Firm — strong manual indicator / Tentative — tool-only]` |

---

### References

<!-- FILL -->

| Source | Link / Identifier |
|---|---|
| NVD | `{{AUTO:nvd_url}}` |
| CWE | `https://cwe.mitre.org/data/definitions/[NNN].html` |
| OWASP | `[https://owasp.org/Top10/A03_2021-Injection/]` |
| Vendor advisory | `[https://vendor.com/security/advisories/CVE-XXXX-XXXXX]` |
| Patch commit | `[https://github.com/vendor/app/commit/[SHA]]` |
| Nuclei template | `[https://github.com/projectdiscovery/nuclei-templates/blob/main/http/cves/...]` |
| CyberPDF vault | `[[real-world-bug-hunting-e112338e]] §[page] / [[hacking-apis-691dcdd7]] §[page]` |

<!--
  ─── END FINDING ────────────────────────────────────────────────────────────
  Repeat the block above (§3 ─── BEGIN FINDING to END FINDING) for each finding.
  ──────────────────────────────────────────────────────────────────────────── -->

---

## §4 — Summary Table

<!-- FILL — one row per finding, ordered by CVSS descending -->

| ID | Target | Severity | CVSS | Finding | Status | Confidence |
|---|---|---|---|---|---|---|
| F-01 | `{{AUTO:host}}` | `{{AUTO:severity}}` | `[0.0]` | `{{AUTO:cve}}` | `[Confirmed / FP / Pending]` | `[Certain / Firm / Tentative]` |

---

## Appendix A — Scan Output Manifest

<!-- OPT -->

| File | Phase | Description |
|---|---|---|
| `{{AUTO:scandir}}/phase1_fast.json` | Phase 1 | Fast recon — common.txt, no extensions |
| `{{AUTO:scandir}}/phase2_ext.json` | Phase 2 | Extension scan — big.txt + web extensions |
| `{{AUTO:scandir}}/phase3_combined.json` | Phase 3 | Combined wordlist + extensions |
| `{{AUTO:scandir}}/phase4_*.json` | Phase 4 | Recursive on directory-like 200s |
| `{{AUTO:scandir}}/phase5_urls.txt` | Phase 5 | Katana JS-aware crawler output |
| `{{AUTO:scandir}}/phase6_params.json` | Phase 6 | Arjun parameter discovery |
| `{{AUTO:scandir}}/phase7_api_ffuf.json` | Phase 7a | API route discovery (ffuf) |
| `{{AUTO:scandir}}/phase7_api_kr.txt` | Phase 7b | API route discovery (kiterunner) |
| `{{AUTO:scandir}}/phase8_nuclei.json` | Phase 8 | Nuclei vulnerability scan (JSONL) |
| `{{AUTO:scandir}}/all_200_urls.txt` | Agg | All 2xx direct hits |
| `{{AUTO:scandir}}/all_redirects.txt` | Agg | All 3xx redirects with destinations |
| `{{AUTO:scandir}}/all_auth_walls.txt` | Agg | All 401/403/405 responses |
| `{{AUTO:scandir}}/open_redirects.txt` | Agg | Open redirect candidates |
| `{{AUTO:scandir}}/adv7FUZZ_*.log` | All | Full scan log (chmod 600) |

---

## Appendix B — Tool Versions

<!-- OPT: capture at scan time with the commands below -->

| Tool | Version | Role |
|---|---|---|
| adv7FUZZ | `{{AUTO:version}}` | Primary orchestrator |
| ffuf | `[ffuf -V]` | Content discovery (Phases 1–3, 7a) |
| nuclei | `[nuclei -version]` | Template-based vuln scan (Phase 8) |
| katana | `[katana -version]` | JS-aware crawler (Phase 5) |
| amass | `[amass -version]` | Subdomain enumeration (Phase 0) |
| arjun | `[arjun --help \| head -1]` | Parameter discovery (Phase 6) |
| kiterunner | `[kr version]` | API route brute-force (Phase 7b) |
| torsocks | `[torsocks --version]` | Tor egress wrapper |

```bash
# Capture tool versions (run from scan environment):
echo "ffuf: $(ffuf -V 2>&1 | head -1)"
echo "nuclei: $(nuclei -version 2>&1 | head -1)"
echo "katana: $(katana -version 2>&1 | head -1)"
echo "amass: $(amass -version 2>&1 | head -1)"
```

---

## Appendix C — Disclosure Timeline

<!-- FILL for coordinated disclosure / OPT for bug bounty (platform manages this) -->

| Date | Event |
|---|---|
| `{{AUTO:date}}` | Initial discovery via adv7FUZZ scan |
| `[YYYY-MM-DD]` | Manual validation completed |
| `[YYYY-MM-DD]` | Report submitted to `[program / vendor]` |
| `[YYYY-MM-DD]` | Program/vendor acknowledgement received |
| `[YYYY-MM-DD]` | Patch released — version `[X.Y.Z]` |
| `[YYYY-MM-DD]` | Patch verified by assessor |
| `[YYYY-MM-DD]` | Public disclosure (if applicable under program policy) |

---

## Appendix D — HackerOne Submission Block

<!--
  Copy-paste ready for HackerOne new report submission.
  Fill this section when submitting. The §3 finding block is the primary record;
  this appendix condenses it to H1 submission format.
  Bracket notation [text] follows H1's own template guidance style.
-->

---

**Title:** `[Short, specific title — e.g.: "Unauthenticated RCE via CVE-2023-30258 in MagnusBilling 7.x at {{AUTO:host}}"]`

**Severity:** `{{AUTO:severity}}`

**App / Version:** `[Application name + version — e.g.: MagnusBilling 7.1.8]`

**OS / Environment:** `[Server OS / N/A — e.g.: Linux (PHP/7.3.33)]`

---

**Summary:** [add summary of the vulnerability]

[2–3 sentences. What is the vulnerability, which component is affected, what can
an attacker do without authentication. Be precise and factual.]

---

**Steps to Reproduce:**

1. [Setup: network position, tools required, authentication state]
2. [Navigate to / send request to: exact URL with method]
3. [Supply payload: exact payload string / parameter value]
4. [Observe: specific HTTP response code, body indicator, timing, OOB callback]

---

**Impact:**

[Business impact in 1–2 paragraphs. Reference affected users, data types, attack
prerequisites (none = unauthenticated), and downstream risk (lateral movement,
data exfiltration, availability impact). Be factual — no speculative escalation
chains that were not validated.]

---

**Supporting Material / References:**

```bash
# Key reproducer command:
[curl command from §3 Evidence section]
```

| Reference | URL |
|---|---|
| NVD | `{{AUTO:nvd_url}}` |
| Vendor patch | `[URL]` |
| Nuclei template | `[URL]` |

---

## Appendix E — Bugcrowd Submission Block

<!--
  Condensed block for Bugcrowd submission.
  Bugcrowd uses VRT (Vulnerability Rating Taxonomy) — fill the VRT field precisely.
-->

---

**VRT Category:** `[e.g.: Server-Side Injection > Remote Code Execution > OS Command Injection]`

**Title:** `[Clear, specific title]`

**Severity (CVSS):** `[0.0] — {{AUTO:severity}}`

**Target:** `{{AUTO:target}}`

---

**Description:**

[Describe the vulnerability: affected component, root cause, exploitation condition.]

---

**Steps to Reproduce:**

1. [Step 1]
2. [Step 2]
3. [Step 3 — observable evidence]

---

**Expected Result:** `[What secure behavior should look like]`

**Actual Result:** `[What the application does — the vulnerable behavior]`

---

**Impact:**

[Business impact statement — data at risk, user population affected, prerequisites.]

---

**Proof of Concept:**

```bash
[Reproducer command / request dump]
```

---

*Report generated by ADVAN7 Offensive Security using adv7FUZZ {{AUTO:version}}*  
*Authorized assessment only — authorization details in §0*  
*Template: ADV7SEC CVE Report Template v1.0*
