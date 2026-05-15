# bbWebScan Wordlist Master Index

## Overview
This master wordlist is compiled from multiple sources optimized for bbWebScan's reconnaissance pipeline.

## Stages & Sources

### Stage 1: Directory & Path Discovery (ffuf, feroxbuster, dirsearch)
- **common.txt** — Kali/SecLists curated common web paths (38K entries)
- **raft-medium-directories.txt** — Raft fuzzing list, medium difficulty (245K entries)
- Used by: ffuf, feroxbuster, dirsearch tools

### Stage 2: Subdomain Enumeration (amass, httpx)
- **subdomains-top1million-5000.txt** — Top 5K subdomains by popularity (30K entries)
- Used by: amass reconnaissance, httpx seed URLs

### Stage 3: Parameter Discovery (arjun stage)
- **Common API/REST parameters** — Extracted typical GraphQL/REST endpoints (~100 entries)
- Used by: arjun parameter discovery

### Stage 4: Username Enumeration (credential testing)
- **top-usernames-shortlist.txt** — Most common usernames for brute-force testing
- Used by: htpasswd, basic-auth reconnaissance

### Stage 5: HTTP Headers (reconnaissance)
- **Common HTTP headers** — Extracted from OWASP, HackerOne, real-world reconnaissance (~80 entries)
- Used by: httpx fingerprinting, Kiterunner API discovery

## Usage

```bash
# Use as bbWebScan default wordlist
bbwebscan scan example.com --wordlist bbwebscan-wordlist-master.txt --mode aggressive --ack-authorized

# Or in a profile YAML (profiles/custom.yaml)
wordlist: /path/to/bbwebscan-wordlist-master.txt

# Load profile and run
bbwebscan scan example.com --profile custom
```

## File Format
Each section is prefixed with a comment header:
```
# ============================================
# Source: <description>
# Entries: <count>
# ============================================
<entries, one per line>
```

## Statistics
- **Total entries**: ~350K+ merged entries
- **File format**: UTF-8, newline-separated, comment-prefixed sections
- **Deduplication**: NOT applied (tools handle duplicates transparently)

## Optimization Tips

### Quick scan (< 5 min)
```bash
grep -v "^#" bbwebscan-wordlist-master.txt | head -1000 > bbwebscan-wordlist-quick.txt
bbwebscan scan example.com --wordlist bbwebscan-wordlist-quick.txt
```

### Remove duplicates
```bash
grep -v "^#" bbwebscan-wordlist-master.txt | sort -u > bbwebscan-wordlist-unique.txt
```

### Extract by stage
```bash
# Only discovery paths
sed -n '/Stage 1/,/Stage 2/p' bbwebscan-wordlist-master.txt | grep -v "^#" > discovery.txt

# Only API parameters
sed -n '/Stage 3/,/Stage 4/p' bbwebscan-wordlist-master.txt | grep -v "^#" > params.txt
```

## Default bbWebScan Wordlist
- System default: `/usr/share/dirb/wordlists/common.txt` (DIRB project)
- Recommended: Use this master file for comprehensive reconnaissance
- Fast mode: Use `common.txt` alone for speed

## References
- Kali/SecLists: https://github.com/danielmiessler/SecLists
- OWASP: https://owasp.org/
- HackerOne: https://hackerone.com/
