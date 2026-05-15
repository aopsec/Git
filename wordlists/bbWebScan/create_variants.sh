#!/bin/bash
set -euo pipefail

echo "=== Creating bbWebScan Wordlist Variants ==="

# Extract wordlist entries (remove comment headers)
grep -v "^#" bbwebscan-wordlist-master.txt | grep -v "^$" > temp_entries.txt

# Variant 1: Unique entries only
echo "Creating unique variant..."
sort -u temp_entries.txt > bbwebscan-wordlist-unique.txt
unique_count=$(wc -l < bbwebscan-wordlist-unique.txt)
echo "  ✓ bbwebscan-wordlist-unique.txt ($unique_count unique entries)"

# Variant 2: Quick scan (first 2000 entries)
echo "Creating quick/fast variant..."
head -2000 temp_entries.txt > bbwebscan-wordlist-quick.txt
quick_count=$(wc -l < bbwebscan-wordlist-quick.txt)
echo "  ✓ bbwebscan-wordlist-quick.txt ($quick_count entries)"

# Cleanup
rm -f temp_entries.txt

echo ""
echo "=== Variants Created ==="
ls -lh bbwebscan-wordlist-*.txt
