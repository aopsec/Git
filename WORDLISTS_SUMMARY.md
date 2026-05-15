# Wordlists Unified Repository - Summary

## ✅ Unification Complete

**Single Location:** `/home/aops/OPia/Git/wordlists/`

Two directories have been consolidated:
- ❌ ~~`/home/aops/OPia/Git/wordlist/` (removed)~~
- ✅ `/home/aops/OPia/Git/wordlists/` (unified structure)

---

## 📊 Repository Contents

### 1. **Kali/SecLists** (`kali/` subdirectory)
Downloaded directly from Kali SecLists project.

| File | Size | Entries | Purpose |
|------|------|---------|---------|
| common.txt | 38K | 4,750 | Common web paths |
| raft-medium-directories.txt | 245K | 29,999 | Directory fuzzing |
| subdomains-top1million-5000.txt | 30K | 5,000 | Subdomain enumeration |
| top-usernames-shortlist.txt | 112B | 17 | Common usernames |

**Total:** 313K, ~40K entries

### 2. **bbWebScan Compiled Wordlists** (`bbWebScan/` subdirectory)
Custom compiled for bbWebScan reconnaissance pipeline.

| File | Size | Entries | Purpose |
|------|------|---------|---------|
| **bbwebscan-wordlist-master.txt** | 315K | 39,991 | **Recommended** - All stages |
| bbwebscan-wordlist-unique.txt | 271K | 33,150 | Deduplicated version |
| bbwebscan-wordlist-quick.txt | 17K | 2,000 | Fast scans (top entries) |

**Total:** 603K, ~75K entries (combined)

**Compilation Sources:**
- ✓ Stage 1: Directory discovery (34.7K entries)
- ✓ Stage 2: Subdomain enumeration (5K entries)
- ✓ Stage 3: API parameters (~150 entries)
- ✓ Stage 4: Usernames (~17 entries)
- ✓ Stage 5: HTTP headers (~80 entries)

### 3. **SecLists Repository** (`SecLists/` subdirectory)
Full Kali SecLists git clone (shallow, depth=1).

| Directory | Content |
|-----------|---------|
| Discovery/ | DNS, Web content discovery |
| Passwords/ | Password wordlists |
| Usernames/ | Username lists |
| Payloads/ | SQL injection, XSS payloads |
| Pattern-Matching/ | Regex patterns |
| Web-Shells/ | Web shell patterns |
| Ai/ | LLM jailbreak & bias testing |

**Size:** 2.5GB (includes all history and indexes)

### 4. **Metadata & Documentation**

| File | Purpose |
|------|---------|
| INDEX.md | Unified repository index & reference |
| README.md | Original Kali/SecLists source info |
| bbWebScan/bbwebscan-wordlist-index.md | Detailed bbWebScan compilation breakdown |

---

## 🚀 Usage Quick Start

### For bbWebScan Scans
```bash
# Comprehensive reconnaissance
bbwebscan scan example.com \
  --wordlist /home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-master.txt \
  --mode aggressive --ack-authorized

# Quick scan (2K entries)
bbwebscan scan example.com \
  --wordlist /home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-quick.txt

# Unique entries only (no duplicates)
bbwebscan scan example.com \
  --wordlist /home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-unique.txt
```

### For Other Tools
```bash
# ffuf directory discovery
ffuf -w wordlists/kali/common.txt -u http://target.com/FUZZ

# Subdomain enumeration
subfinder -l wordlists/kali/subdomains-top1million-5000.txt

# DNS brute-forcing
dnsenum -f wordlists/kali/subdomains-top1million-5000.txt target.com

# Full SecLists access
ls -la wordlists/SecLists/Discovery/Web-Content/
```

---

## 📁 Directory Tree

```
/home/aops/OPia/Git/wordlists/
├── bbWebScan/                              # ← New compiled wordlists
│   ├── bbwebscan-wordlist-master.txt       # ← **RECOMMENDED for bbWebScan**
│   ├── bbwebscan-wordlist-unique.txt       # Deduplicated
│   ├── bbwebscan-wordlist-quick.txt        # Fast variant (2K entries)
│   ├── bbwebscan-wordlist-index.md         # Detailed documentation
│   ├── compile_bbwebscan_wordlists.sh      # Regenerate from sources
│   └── create_variants.sh                  # Create unique/quick variants
│
├── kali/                                   # ← Kali SecLists extracts
│   ├── common.txt
│   ├── raft-medium-directories.txt
│   ├── subdomains-top1million-5000.txt
│   └── top-usernames-shortlist.txt
│
├── SecLists/                               # ← Full repository (2.5GB)
│   ├── Discovery/
│   ├── Passwords/
│   ├── Usernames/
│   ├── Payloads/
│   ├── Pattern-Matching/
│   ├── Web-Shells/
│   ├── Ai/
│   └── ...
│
├── INDEX.md                                # ← Read this first!
└── README.md                               # Original source documentation
```

---

## 🔄 Maintenance

### Regenerate bbWebScan Wordlists
```bash
cd /home/aops/OPia/Git/wordlists/bbWebScan
bash compile_bbwebscan_wordlists.sh  # Recompile master from kali/ sources
bash create_variants.sh               # Regenerate unique & quick variants
```

### Update Kali Extracts
```bash
# Download new Kali wordlists manually
cd /home/aops/OPia/Git/wordlists/kali
curl -fsSL <URL> -o <filename>

# Then regenerate bbWebScan wordlists
cd /home/aops/OPia/Git/wordlists/bbWebScan
bash compile_bbwebscan_wordlists.sh
```

### Refresh SecLists
```bash
cd /home/aops/OPia/Git/wordlists
rm -rf SecLists/
git clone --depth 1 https://github.com/danielmiessler/SecLists.git
```

---

## 📊 Statistics

| Metric | Value |
|--------|-------|
| Total size | 2.5 GB |
| Active wordlists | ~1 MB |
| Master entries (bbWebScan) | 39,991 |
| Unique entries | 33,150 |
| Quick variant | 2,000 |
| Directories | 4 (bbWebScan, kali, SecLists, blackarch) |
| Documentation files | 3 (INDEX.md, README.md, bbwebscan-wordlist-index.md) |

---

## ✨ Key Features

✅ **Unified Structure** — Single `/wordlists/` directory with organized subdirectories
✅ **bbWebScan Ready** — Pre-compiled master wordlist optimized for 5-stage pipeline
✅ **Multiple Variants** — Master, unique, and quick options for different scan profiles
✅ **Fully Documented** — INDEX.md, detailed compilation breakdown, usage examples
✅ **Maintainable** — Scripts to regenerate all variants from source
✅ **Extensible** — Easy to add new wordlists or customize variants
✅ **No Duplicates** — Separate unique variant for efficiency-critical scans

---

## 🎯 Recommended Workflow

1. **First-time setup:**
   ```bash
   # Verify wordlists exist
   ls -lh /home/aops/OPia/Git/wordlists/bbWebScan/
   ```

2. **bbWebScan scans:**
   ```bash
   bbwebscan scan target.com \
     --wordlist /home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-master.txt \
     --mode aggressive --ack-authorized
   ```

3. **Update profile:**
   ```yaml
   # Edit: /home/aops/OPia/Git/ObsidianAgent/Projects/bbWebScan/profiles/custom.yaml
   wordlist: /home/aops/OPia/Git/wordlists/bbWebScan/bbwebscan-wordlist-master.txt
   ```

4. **Run with profile:**
   ```bash
   bbwebscan scan target.com --profile custom --ack-authorized
   ```

---

**Status:** ✅ Complete & Ready for Use  
**Last Updated:** 2026-05-15  
**Maintainer:** Copilot CLI  

For detailed bbWebScan integration, see: `wordlists/bbWebScan/bbwebscan-wordlist-index.md`
