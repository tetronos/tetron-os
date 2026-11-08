#!/bin/sh
# Install each built deb in a clean debian:trixie container and check it.
# Usage: packaging/tests/test-debs.sh   (needs docker; build with `make debs` first)
# Then installs the metapackages from a local apt repository in a second clean container,
# and upgrades the previous GitHub release to this build in a third (packaging/manifest.toml
# rules). Without network that step is skipped, unless REQUIRE_UPGRADE_TEST=1 (release workflow).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$(dirname "$HERE")"
PIN="$(dirname "$PKG")/config/common/archives/kmscon-backports.pref.chroot"
[ -d "$PKG/out" ] && ls "$PKG"/out/*.deb >/dev/null 2>&1 || { echo "no debs in $PKG/out; run: make debs" >&2; exit 1; }
# Only the debs this manifest makes (hard links in a fresh staging dir): out/
# keeps older builds, which apt would otherwise take as newer.
DEBS="$PKG/cache/test-debs"
rm -rf "$DEBS" && mkdir -p "$DEBS"
for f in $(python3 "$PKG/build.py" --list-debs); do
	[ -f "$PKG/out/$f" ] || { echo "missing $PKG/out/$f; run: make debs" >&2; exit 1; }
	ln "$PKG/out/$f" "$DEBS/$f" 2>/dev/null || cp "$PKG/out/$f" "$DEBS/$f"
done
python3 "$PKG/build.py" --list-tests > "$DEBS/tests.list"
docker run --rm -v "$DEBS:/debs:ro" -v "$HERE/in-container.sh:/in-container.sh:ro" -v "$PIN:/kmscon-backports.pref:ro" \
	debian:trixie sh /in-container.sh
docker run --rm -v "$DEBS:/debs:ro" -v "$HERE/meta-in-container.sh:/meta-in-container.sh:ro" -v "$PIN:/kmscon-backports.pref:ro" \
	debian:trixie sh /meta-in-container.sh

# The previous release's attached packages, checked against its SHA256SUMS, kept per tag.
REL=https://github.com/tetronos/tetron-os/releases
tag=$(curl -fsSLo /dev/null -w '%{url_effective}' "$REL/latest" 2>/dev/null | sed -n 's#.*/tag/##p')
PREV="$PKG/cache/prev-release/$tag"
if [ -n "$tag" ] && { [ -f "$PREV/ok" ] || {
	mkdir -p "$PREV" && curl -fsSL -o "$PREV/SHA256SUMS" "$REL/download/$tag/SHA256SUMS" &&
	for f in $(awk '{print $2}' "$PREV/SHA256SUMS"); do curl -fsSL -o "$PREV/$f" "$REL/download/$tag/$f" || break; done &&
	(cd "$PREV" && sha256sum -c --quiet SHA256SUMS) && touch "$PREV/ok"; }; }; then
	echo "== upgrade test from $tag"
	docker run --rm -v "$DEBS:/debs:ro" -v "$PREV:/prev:ro" -v "$HERE/upgrade-in-container.sh:/upgrade-in-container.sh:ro" \
		-v "$PIN:/kmscon-backports.pref:ro" debian:trixie sh /upgrade-in-container.sh
elif [ "${REQUIRE_UPGRADE_TEST:-0}" = 1 ]; then
	echo "FAIL upgrade test: could not get the previous release" >&2; exit 1
else
	echo "SKIP upgrade test: could not get the previous release"
fi
