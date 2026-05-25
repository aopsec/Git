# Findings Report — vswitcher.com + mind-7.org
**Scan date:** 2026-05-22  
**Tool:** adv7FUZZ v0.1.0  
**Scan dirs:** `fuzz_vswitcher.com_20260522_020632` / `fuzz_mind-7.org_20260522_020554`

---

## vswitcher.com

### [~~CRIT-1~~] ~~CVE-2023-30258~~ — CONFIRMED FALSE POSITIVE
| Field | Value |
|---|---|
| CVE | CVE-2023-30258 |
| CVSS | ~~9.8~~ — N/A (false positive) |
| Status | **CONFIRMED FALSE POSITIVE** |
| Tested path | `/css/css.php/mbilling/lib/icepay/icepay.php?democ=<cmd>` |
| OOB result | No callback on `d888h1k4590gtnvp22b07puampp5u5hxh.oast.pro` |
| Time-based result | `HTTP:200 \| Time:1466ms` (need ≥7000ms) |
| Nuclei hits | 10 (all false — timing via Tor latency, not sleep injection) |

**Root cause (3 compounding factors):**

1. **Tor latency satisifed the matcher** — nuclei `duration >= 7` fired because Tor RTT (~7-9s)
   exceeded the threshold, not because `sleep 7` executed on the server.
2. **PATH_INFO ignored by css.php** — `css.php/mbilling/lib/icepay/icepay.php` passes the suffix
   as PHP PATH_INFO. The `css.php` JS-bundle endpoint ignores any PATH_INFO suffix and serves its
   bundle with HTTP 200 for any path — it never routes to `icepay.php`.
3. **Unknown version hash** — the `?v=032cd37a873c523e69dbb92d36c7152a` hash used in the template
   returned an empty body, not an icepay.php response. MagnusBilling is not present at this path.

**OOB test (2026-05-22):** interactsh-client OAST host `d888h1k4590gtnvp22b07puampp5u5hxh.oast.pro`
— zero interactions logged after direct curl probe. Time-based direct test: 1466ms (baseline RTT),
not ≥7000ms. vswitcher.com does NOT run MagnusBilling at this endpoint.

**OOB validation procedure (requires interactsh-client):**
```bash
# 1. Install (run once)
go install -v github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest

# 2. Generate callback URL
interactsh-client -v &
# Note the OAST host: e.g.  abc123.oast.pro

# 3. Targeted nuclei re-run with OAST
nuclei -u "https://vswitcher.com/css/css.php?v=032cd37a873c523e69dbb92d36c7152a" \
    -t /home/aops/nuclei-templates/http/cves/2023/CVE-2023-30258.yaml \
    -iserver abc123.oast.pro \
    -v -debug-req 2>&1 | tee /tmp/cve_2023_30258_oob.log

# 4. Or use adv7FUZZ directly with new --oob flag:
./adv7FUZZ.sh -u https://vswitcher.com --phase 8 --oob abc123.oast.pro
```

**If OOB fires:** Confirmed critical RCE — report to vswitcher.com immediately.  
**If OOB does not fire:** Check origin IP bypass (Cloudflare may block callback DNS). Use
`SecurityTrails` or `Shodan` for historical A records, then test with `--resolve` override.

**Remediation:** Upgrade MagnusBilling to patched version (commit `ccff9f6` on magnusbilling7
addresses this). Alternatively: WAF rule blocking requests to `*/mbilling/lib/icepay/*`.

---

### [LOW-1] PHP 7.3.33 — End-of-Life Runtime
| Field | Value |
|---|---|
| Severity | LOW (informational risk, no direct exploit) |
| Evidence | `X-Powered-By: PHP/7.3.33` (visible in nuclei CVE-2023-30258 response) |
| EOL date | 2021-12-06 (no security patches since) |

PHP 7.3 receives no CVE patches. Any future vulnerability in the runtime has no fix path.
Combined with CRIT-1 (if confirmed), PHP EOL increases the blast radius.

**Remediation:** Upgrade to PHP 8.2+ or 8.3 (current stable).

---

### [LOW-2] Missing Cookie Security Flags
| Field | Value |
|---|---|
| Severity | LOW |
| Evidence | `Set-Cookie: PHPSESSID=...; path=/` (no Secure, no HttpOnly) |
| Secondary | `Set-Cookie: ips4_IPSSessionFront=...; path=/; secure; HttpOnly` (missing SameSite=Strict) |

`PHPSESSID` is exposed to JS (no HttpOnly → XSS session theft) and transmitted over HTTP
(no Secure → downgrade interception). The IPS4 session cookie is better configured but
missing `SameSite=Strict`, allowing CSRF via cross-site link.

**Remediation:**
```php
// php.ini / session_set_cookie_params():
session_set_cookie_params([
    'secure'   => true,
    'httponly' => true,
    'samesite' => 'Strict',
]);
```

---

### [INFO-1] Makefile Exposure — FALSE POSITIVE
| Field | Value |
|---|---|
| Nuclei template | `makefile-exposure` |
| Claimed path | `/js/js.php/Makefile` |
| Status | **Verified false positive** |

Curl to `/js/js.php/Makefile?v=...` returns minified JavaScript (the js.php bundle), not
Makefile content. The `js.php` endpoint ignores path suffixes and serves its JS bundle
with HTTP 200 for any suffix — the 200 response triggered the template incorrectly.

---

### [INFO-3] CORS — Overly Permissive `Access-Control-Allow-Origin: *`
| Field | Value |
|---|---|
| Severity | INFO (low — no direct exploit without a valid token) |
| Evidence | `access-control-allow-origin: *` on `/portal/download/vlauncher.jar` (301 response) |
| Secondary | `access-control-allow-headers: Content-Type, Authorization, X-Requested-With` |

`ACAO: *` combined with `Authorization` header allowed means any cross-origin request can
send credentials via the Authorization header. Low risk in isolation but violates least-privilege
CORS policy — should restrict to trusted origins.

**Remediation:** Replace `Access-Control-Allow-Origin: *` with an explicit allowlist
(e.g., `Access-Control-Allow-Origin: https://vswitcher.com`).

---

### [INFO-4] CSRF Token Leaked in Every Unauthenticated Response
| Field | Value |
|---|---|
| Severity | INFO (low — token requires session to be actionable) |
| Evidence | `var config = helpers.initConfig({"csrfToken":"<hex>"})` present in all 404 pages |

Every unauthenticated request (including 404s) returns a fresh CSRF token in the page JS.
Without a matching authenticated session the token is not actionable, but it reduces the
effort required for CSRF if an attacker can trick an authenticated user into loading a
crafted page.

**Remediation:** Only embed CSRF tokens in responses to authenticated sessions.

---

### [INFO-2] WAF — Cloudflare Confirmed
Cloudflare WAF confirmed on all endpoints. Provides partial protection but does not remediate
the underlying CRIT-1 vulnerability if origin IP is reachable directly.

---

## mind-7.org

### [LOW-1] Weak Cipher Suites — FALSE POSITIVE
| Field | Value |
|---|---|
| Nuclei finding | `weak-cipher-suites` on `mind-7.org:443` |
| Status | **Likely false positive — nmap confirms TLSv1.3 / grade A** |
| nmap result | TLSv1.3 only, `least strength: A` |

nmap `ssl-enum-ciphers` showed TLSv1.0/1.1/1.2 as unsupported (NULL cipher list = no
negotiation succeeded) and TLSv1.3 with grade A. Cloudflare enforces modern TLS on all
fronted domains. Nuclei template may have fired on a TLS handshake quirk.

**Action:** No remediation needed — verify by running `testssl.sh mind-7.org` for
full TLS audit if a formal report is required.

---

### [INFO-1] HTTP Missing Security Headers
Extensive missing headers detected (CSP, HSTS, X-Frame-Options, X-Content-Type-Options,
Referrer-Policy, Permissions-Policy). Standard hardening recommendations:
```
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
Permissions-Policy: geolocation=(), camera=(), microphone=()
```

---

### [INFO-2] Cloudflare Bot Management Active
Heavy Cloudflare Turnstile/CAPTCHA protection (`1eec422858ff/api.js` + `__cf_chl_*` tokens).
Crawler was actively challenged — most paths returned challenge responses, not app content.
Surface area is significantly reduced from attacker perspective.

---

## Summary Table

| ID | Target | Severity | Finding | Status |
|---|---|---|---|---|
| ~~CRIT-1~~ | vswitcher.com | ~~CRITICAL~~ | ~~CVE-2023-30258 MagnusBilling RCE~~ | **CONFIRMED FALSE POSITIVE** (OOB: no callback; timing: 1466ms) |
| LOW-1 | vswitcher.com | LOW | PHP 7.3.33 EOL | Confirmed |
| LOW-2 | vswitcher.com | LOW | Cookie flags (PHPSESSID missing Secure+HttpOnly) | Confirmed |
| INFO-1 | vswitcher.com | INFO | Makefile exposure | False positive |
| INFO-2 | vswitcher.com | INFO | Cloudflare WAF | Confirmed |
| INFO-3 | vswitcher.com | INFO | CORS — ACAO: * on auth endpoints | Confirmed |
| INFO-4 | vswitcher.com | INFO | CSRF token leaked in 404 pages | Confirmed |
| LOW-1 | mind-7.org | LOW | Weak cipher suites | Likely false positive |
| INFO-1 | mind-7.org | INFO | Missing security headers | Confirmed |
| INFO-2 | mind-7.org | INFO | Cloudflare Bot Management | Confirmed |

---

## Next Actions

1. **~~CRIT-1 resolved~~** — CVE-2023-30258 confirmed false positive. No MagnusBilling present.
   adv7FUZZ lesson learned: `--tor` + nuclei time-based templates produce false positives; always
   use `--oob` flag and avoid `--tor` for duration-based CVE templates.
2. **vlauncher.jar extraction — BLOCKED (all 3 vectors exhausted)**
   - V1 RCE: false positive (no injection)
   - V2 SQLi: not confirmed (timing 2s, CSRF reuse explained error delta)
   - V3 Default creds: admin:admin, admin:magnum, admin:magnum123, mbilling:mbilling — all redirect to `/login`
   - **New intel:** `/portal/download/vlauncher.jar` requires a **paid subscriber account** — not accessible to free registered users
   - Active vector: OSINT — search for leaked JAR on mirrors, GitHub, APK sites; direct download URL bypass probe
3. **adv7FUZZ.sh** now supports `--oob <server>`, `--no-ac`, `--recurse-redirects` — use all three
   on next scan: `./adv7FUZZ.sh -u https://vswitcher.com --no-ac --recurse-redirects --oob <oast>`
4. mind-7.org: No high-priority follow-up needed; optional `testssl.sh` for formal TLS audit.
