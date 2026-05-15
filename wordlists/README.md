# Kali & BlackArch Wordlists

## Contents

### Kali/SecLists Wordlists
- **common.txt** - Common web paths and directories
- **subdomains-top1million-5000.txt** - Top subdomains by popularity
- **raft-medium-directories.txt** - Raft directory fuzzing list
- **top-10000-passwords.txt** - Top common passwords
- **dns-bruteforce.txt** - DNS brute-forcing list
- **top-usernames-shortlist.txt** - Common usernames

### BlackArch Wordlists
- commonspeak2.txt - Web paths from live sites (Assetnote)

## Usage

```bash
# Web directory discovery
ffuf -w kali/common.txt -u http://target.com/FUZZ

# Subdomain enumeration
subfinder -l kali/subdomains-top1million-5000.txt

# DNS brute-forcing
dnsenum -f kali/dns-bruteforce.txt target.com

# Password attacks
hydra -l admin -P kali/top-10000-passwords.txt ssh://target.com
```

## Sources
- Kali/SecLists: https://github.com/danielmiessler/SecLists
- Assetnote: https://assetnote.io
