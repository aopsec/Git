#!/bin/bash
set -euo pipefail

echo "=== Unifying Wordlist Directories ==="
echo ""

# Keep: /home/aops/OPia/Git/wordlists (source)
# Move: /home/aops/OPia/Git/wordlist/bbWebScan → /home/aops/OPia/Git/wordlists/bbWebScan

echo "Current structure:"
tree -L 2 -h wordlists/ 2>/dev/null || find wordlists -type d | sort
echo ""
tree -L 2 -h wordlist/ 2>/dev/null || find wordlist -type d | sort

echo ""
echo "Moving bbWebScan directory into unified structure..."
mkdir -p wordlists/bbWebScan
mv wordlist/bbWebScan/* wordlists/bbWebScan/ 2>/dev/null || true

echo "Removing old wordlist directory..."
rmdir wordlist/bbWebScan 2>/dev/null || true
rmdir wordlist 2>/dev/null || true

echo ""
echo "=== Final Unified Structure ==="
tree -h -L 2 wordlists/ 2>/dev/null || find wordlists -type f -o -type d | head -30

echo ""
echo "=== Directory Summary ==="
du -sh wordlists/
du -sh wordlists/kali/
du -sh wordlists/bbWebScan/
du -sh wordlists/SecLists/

echo ""
echo "✓ Unification complete! Single directory: /home/aops/OPia/Git/wordlists"
