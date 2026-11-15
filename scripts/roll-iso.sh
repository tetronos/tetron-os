#!/bin/sh
# Roll TetronOS ISOs: check the repos, check the pins, test packaging, build.
# Usage: scripts/roll-iso.sh [edition ...]   (default: server desktop)
# Run from anywhere; sibling component repos are expected next to this one.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODE="${CODE:-$(dirname "$ROOT")}"
ORG="${ORG:-tetronos}"
EDITIONS="${*:-server desktop}"
COMPONENTS="tetron tetron-tui tetron-wm tetron-browser tetron-appstore"
cd "$ROOT"
fail=0

echo "== 1. repos clean and in sync with origin"
for r in tetron-os $COMPONENTS tetron-packaging tetronos-apt; do
	d="$CODE/$r"; [ -d "$d/.git" ] || { echo "MISSING $d"; fail=1; continue; }
	git -C "$d" fetch -q || { echo "FETCH FAILED $r"; fail=1; continue; }
	dirty=$(git -C "$d" status --porcelain | wc -l)
	lr=$(git -C "$d" rev-list --left-right --count HEAD...@{u} 2>/dev/null || echo "? ?")
	echo "$r branch=$(git -C "$d" branch --show-current) dirty=$dirty ahead/behind=$lr"
	[ "$dirty" = 0 ] || fail=1
done

echo "== 2. manifest pins match the latest published releases"
for r in $COMPONENTS; do
	pin=$(awk -v n="$r" '$0 == "name = \"" n "\"" {f=1} f && /^version/ {gsub(/[^0-9.]/, "", $3); print $3; exit}' packaging/manifest.toml)
	latest=$(git ls-remote --tags --refs "https://github.com/$ORG/$r" 'v[0-9]*' 2>/dev/null | sed 's#.*refs/tags/v##' | grep -v -- '-' | sort -V | tail -1)
	if [ "$pin" = "$latest" ]; then echo "ok    $r $pin"; else echo "DIFF  $r pinned=$pin latest=$latest"; fail=1; fi
done

[ "$fail" = 0 ] || { echo "Checks failed. Fix the lines above (update packaging/manifest.toml, commit, pull) and run again."; exit 1; }

echo "== 3. packaging: build the debs and run the unit tests"
python3 packaging/build.py
python3 packaging/tests/test_build.py

echo "== 4. spec constraints"
python3 reconcile.py

echo "== 5. build the ISOs"
[ -d build/vm ] || make vm-create
for e in $EDITIONS; do make iso EDITION="$e"; done
ls -lh out/*"$(date +%Y%m%d)"*.iso
