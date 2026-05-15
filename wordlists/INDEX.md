# Unified Wordlist Repository

**Location:** `/home/aops/OPia/Git/wordlists/`

## Directory Structure

```
wordlists/
├── kali/                          # Kali/SecLists extracts (direct downloads)
│   ├── common.txt                 # Common web paths
│   ├── raft-medium-directories.txt # Directory fuzzing
│   ├── subdomains-top1million-5000.txt
│   └── top-usernames-shortlist.txt
│
├── bbWebScan/                     # Compiled for bbWebScan project
│   ├── bbwebscan-wordlist-master.txt        # Complete (39.9K entries)
│   ├── bbwebscan-wordlist-unique.txt        # Deduplicated (33.1K unique)
│   ├── bbwebscan-wordlist-quick.txt         # Fast variant (2K entries)
│   ├── bbwebscan-wordlist-index.md          # Detailed index
│   └── compile_bbwebscan_wordlists.sh       # Regeneration script
│
├── SecLists/                      # Full Kali SecLists repository
│   ├── Discovery/
│   ├── Passwords/
│   ├── Usernames/
│   └── ...
│
├── README.md                      # Initial sources documentation
└── INDEX.md                       # This file

```

## Quick Reference

### For bbWebScan Users
```bash
# Comprehensive scan
bbwebscan scan example.com \
  --wordlist /home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-master.txt \
  --mode aggressive --ack-authorized

# Quick scan
bbwebscan scan example.com \
  --wordlist /home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-quick.txt

# Via profile (profiles/aggressive.yaml)
wordlist: /home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-master.txt
```

### For General Use
```bash
# Directory discovery
ffuf -w wordlists/kali/common.txt -u http://target.com/FUZZ

# Subdomain enumeration
subfinder -l wordlists/kali/subdomains-top1million-5000.txt

# From SecLists (if needed)
# Explore: wordlists/SecLists/Discovery/
# Explore: wordlists/SecLists/Passwords/
```

## File Sizes & Entry Counts

| Wordlist | Size | Entries | Purpose |
|----------|------|---------|---------|
| common.txt | 38K | 4.7K | Common paths |
| raft-medium-directories.txt | 245K | 30K | Dir fuzzing |
| subdomains-top1million-5000.txt | 30K | 5K | DNS enum |
| bbwebscan-wordlist-master.txt | 315K | 39.9K | **All stages** |
| bbwebscan-wordlist-unique.txt | 271K | 33.1K | Deduped |
| bbwebscan-wordlist-quick.txt | 17K | 2K | Fast scans |

## bbWebScan Compilation Details

The master wordlist merges 5 stages:

1. **Directory Discovery** (34.7K entries)
   - common.txt + raft-medium-directories.txt
   - Used by: ffuf, feroxbuster, dirsearch

2. **Subdomain Enumeration** (5K entries)
   - Top subdomains
   - Used by: amass, httpx

3. **API Parameters** (~150 entries)
   - REST/GraphQL common parameters
   - Used by: arjun

4. **Usernames** (~17 entries)
   - Common credentials
   - Used by: basic auth reconnaissance

5. **HTTP Headers** (~80 entries)
   - Reconnaissance headers
   - Used by: httpx, kiterunner

**Total: 39.9K entries, 315K file size**

See `bbWebScan/bbwebscan-wordlist-index.md` for detailed breakdown.

## Maintenance

### Regenerate bbWebScan wordlists
```bash
cd /home/aops/OPia/Git/wordlists/bbWebScan
bash compile_bbwebscan_wordlists.sh
bash create_variants.sh
```

### Update Kali wordlists (manual, as needed)
```bash
# From Kali SecLists repo
cd /home/aops/OPia/Git/wordlists/kali
curl -fsSL <URL> -o filename.txt
```

### Recreate SecLists (full repo)
```bash
cd /home/aops/OPia/Git/wordlists
git clone --depth 1 https://github.com/danielmiessler/SecLists.git
```

## Integration Points

### bbWebScan Project
- Recommended: `bbWebScan/bbwebscan-wordlist-master.txt`
- Location: `/home/aops/OPia/Git/ObsidianAgent/Projects/bbWebScan/`

### Other Tools
- ffuf, feroxbuster, dirsearch: `kali/common.txt` or `raft-medium-directories.txt`
- DNS tools (dnsenum): `kali/subdomains-top1million-5000.txt`
- Full SecLists: `SecLists/` subdirectories

## Sources

- **Kali/SecLists**: https://github.com/danielmiessler/SecLists
- **DIRB**: System default `/usr/share/dirb/wordlists/common.txt`
- **OWASP**: https://owasp.org/
- **Compilation**: Custom aggregation for bbWebScan reconnaissance

## Notes

- All files are UTF-8, newline-separated
- Comment lines in master files start with `#`
- No automatic deduplication in master (tools handle transparently)
- Use `bbwebscan-wordlist-unique.txt` if concerned about redundancy
- Use `bbwebscan-wordlist-quick.txt` for fast preliminary scans

---

**Last Updated:** 2026-05-15
**Total Size:** 2.5G (mostly SecLists repo)
**Active Files:** ~1MB (excluding SecLists)
