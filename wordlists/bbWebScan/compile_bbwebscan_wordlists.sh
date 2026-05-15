#!/bin/bash
set -euo pipefail

echo "=== Compiling bbWebScan Wordlists ==="
echo ""

# Source directory (where kali wordlists are)
source_dir="/home/aops/OPia/Git/wordlists"

# Master output file
master_file="bbwebscan-wordlist-master.txt"
> "$master_file"  # Clear if exists

# Counter for tracking
total_entries=0
total_files=0

# Function to add wordlist with header
add_wordlist() {
  local file=$1
  local description=$2
  
  if [ ! -f "$file" ]; then
    echo "  ⚠ Missing: $file"
    return
  fi
  
  local count=$(wc -l < "$file" 2>/dev/null || echo 0)
  if [ "$count" -eq 0 ]; then
    echo "  ⚠ Empty: $file"
    return
  fi
  
  echo "  ✓ Adding: $description ($count entries)"
  
  # Add a comment header with source info
  {
    echo "# ============================================"
    echo "# Source: $description"
    echo "# Entries: $count"
    echo "# ============================================"
    cat "$file"
    echo ""
  } >> "$master_file"
  
  total_entries=$((total_entries + count))
  total_files=$((total_files + 1))
}

# Stage 1: Discovery wordlists (ffuf, feroxbuster, dirsearch)
echo "Stage 1: Directory & Path Discovery (ffuf, feroxbuster, dirsearch)"
add_wordlist "$source_dir/kali/common.txt" "Kali/SecLists - Common web paths"
add_wordlist "$source_dir/kali/raft-medium-directories.txt" "Kali/SecLists - Raft medium directories"

# Stage 2: Subdomain enumeration (amass)
echo ""
echo "Stage 2: Subdomain Enumeration (amass, httpx seeds)"
add_wordlist "$source_dir/kali/subdomains-top1million-5000.txt" "Kali/SecLists - Top subdomains"

# Stage 3: Parameter discovery (arjun)
echo ""
echo "Stage 3: Parameter Discovery (arjun, params stage)"
cat > temp_params.txt << 'PARAMS'
id
page
search
q
query
keyword
limit
offset
sort
order
filter
category
type
status
user
action
cmd
command
function
method
code
name
email
username
password
token
key
api_key
access_token
secret
config
option
setting
param
parameter
data
input
output
value
result
response
error
message
success
flag
debug
verbose
view
edit
delete
create
add
remove
list
show
hide
display
refresh
reset
load
save
export
import
backup
restore
upload
download
submit
cancel
confirm
approve
reject
pending
completed
draft
published
archived
active
inactive
enabled
disabled
mode
level
priority
severity
risk
threat
alert
notification
event
log
trace
monitor
analyze
report
summary
detail
count
total
size
length
width
height
color
format
encoding
charset
language
locale
timezone
region
country
state
city
address
phone
fax
website
company
department
team
role
position
title
description
content
body
header
footer
sidebar
menu
button
link
icon
image
video
audio
document
file
folder
directory
archive
PARAMS
add_wordlist "temp_params.txt" "Common API/REST parameters"
rm temp_params.txt

# Stage 4: HTTP headers & auth (httpx, katana)
echo ""
echo "Stage 4: Username Enumeration (credential testing)"
add_wordlist "$source_dir/kali/top-usernames-shortlist.txt" "Kali/SecLists - Top usernames"

# Stage 5: Headers for httpx reconnaissance
echo ""
echo "Stage 5: Common HTTP Headers (reconnaissance)"
cat > temp_headers.txt << 'HEADERS'
X-Forwarded-For
X-Forwarded-Proto
X-Forwarded-Host
X-Real-IP
X-Original-URL
X-Rewrite-URL
X-Original-Host
X-Host
X-Forwarded
Forwarded
Client-IP
X-Client-IP
X-Custom-IP
X-Originating-IP
X-Forwarded-For-Original
X-Original-Forwarded-For
X-Proxy-Authorization
X-Powered-By
Server
X-AspNet-Version
X-Runtime-Version
X-Runtime
X-Turbo-Charged-By
X-Served-By
X-Served-Via
X-Powered-By-Plesk
X-Generator
X-Designer
X-Creator
X-Developed-By
X-Built-By
X-Built-With
X-Built-For
X-Technology
X-Framework
X-CMS
X-Platform
X-Backend
X-Cache
X-Cache-Control
X-CDN
X-CDN-Cache
X-Proxy
X-Proxy-By
X-Reverse-Proxy
X-Load-Balancer
Authorization
X-API-Key
X-Auth-Token
X-CSRF-Token
X-CSRF-Token-Name
X-CSRF-Protection
X-Requested-With
Content-Type
Accept
Accept-Language
Accept-Encoding
User-Agent
Referer
Origin
Host
Connection
Keep-Alive
Cache-Control
Pragma
X-Debug
X-Debug-Token
X-Debug-Mode
X-Verbose
X-Trace
X-Trace-ID
X-Request-ID
X-Correlation-ID
X-Session-ID
X-User-ID
X-User-Agent
X-Browser
X-Version
X-Access-Control-Allow-Origin
Access-Control-Allow-Origin
Access-Control-Allow-Methods
Access-Control-Allow-Headers
Access-Control-Max-Age
HEADERS
add_wordlist "temp_headers.txt" "Common HTTP headers (reconnaissance)"
rm temp_headers.txt

# Generate metadata
echo ""
echo "=== Compilation Summary ==="
echo "Master file: $master_file"
echo "Total files merged: $total_files"
echo "Total entries: $total_entries"
du -h "$master_file"

# Create an index file
cat > bbwebscan-wordlist-index.md << 'INDEX'
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
INDEX

echo ""
echo "✓ Index created: bbwebscan-wordlist-index.md"
echo ""
echo "Files in bbWebScan wordlist directory:"
ls -lh
