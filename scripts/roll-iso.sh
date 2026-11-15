#!/bin/sh
# Roll TetronOS ISOs: check the repo, check the pins, test packaging, build.
# Usage: scripts/roll-iso.sh [edition ...]
#   editions: server, server-fw (server with all firmware), desktop
#   default:  server server-fw desktop
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EDITIONS="${*:-server server-fw desktop}"
cd "$ROOT"
fail=0

echo "== 1. this repository is clean and in sync with origin"
git fetch -q || { echo "git fetch failed"; fail=1; }
dirty=$(git status --porcelain | wc -l)
lr=$(git rev-list --left-right --count HEAD...@{u} 2>/dev/null || echo "no-upstream")
echo "branch=$(git branch --show-current) uncommitted=$dirty ahead/behind=$lr"
[ "$dirty" = 0 ] || { echo "Uncommitted changes: commit or stash them."; fail=1; }

echo "== 2. manifest pins match the latest published releases"
python3 scripts/pins.py check || fail=1

[ "$fail" = 0 ] || { echo "Checks failed. Fix the lines above (python3 scripts/pins.py update, review git diff, commit) and run again."; exit 1; }

echo "== 3. packaging: build the debs and run the unit tests"
python3 packaging/build.py
python3 packaging/tests/test_build.py

echo "== 4. spec constraints"
python3 reconcile.py > /dev/null

echo "== 5. build the ISOs"
[ -d build/vm ] || make vm-create
for e in $EDITIONS; do
	case "$e" in
		server-fw) make iso EDITION=server FIRMWARE=all ;;
		server|desktop) make iso EDITION="$e" ;;
		*) echo "unknown edition: $e (server, server-fw, desktop)" >&2; exit 1 ;;
	esac
done
ls -lh out/*"$(date +%Y%m%d)"*.iso
