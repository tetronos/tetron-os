#!/bin/sh
# Install each built deb in a clean debian:trixie container and check it.
# Usage: packaging/tests/test-debs.sh   (needs docker; build with `make debs` first)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$(dirname "$HERE")"
[ -d "$PKG/out" ] && ls "$PKG"/out/*.deb >/dev/null 2>&1 || { echo "no debs in $PKG/out; run: make debs" >&2; exit 1; }
python3 "$PKG/build.py" --list-tests > "$PKG/out/tests.list"
docker run --rm -v "$PKG/out:/debs:ro" -v "$HERE/in-container.sh:/in-container.sh:ro" \
	debian:trixie sh /in-container.sh
