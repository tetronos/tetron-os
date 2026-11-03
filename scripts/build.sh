#!/bin/sh
# Runs inside the build environment (VM or container). Assembles config/common + config/$EDITION
# into /build/$EDITION and runs live-build there.
set -e
EDITION="${EDITION:-server}"
# Firmware is its own axis; each edition has a default.
case "$EDITION" in
	server)  FIRMWARE="${FIRMWARE:-none}" ;;
	desktop) FIRMWARE="${FIRMWARE:-all}" ;;
	*) echo "unknown EDITION: $EDITION" >&2; exit 1 ;;
esac
SUFFIX=""; [ "$FIRMWARE" = all ] && SUFFIX="-fw"
SRC="${SRC:-/src}"
WORK="${WORKROOT:-/build}/$EDITION"
OUTDIR="${OUTDIR:-/out}"
mkdir -p "$WORK"
cd "$WORK"
rm -rf auto config/package-lists config/includes.chroot config/hooks config/archives config/packages.chroot
mkdir -p config
cp -a "$SRC/auto" .
for d in "$SRC/config/common" "$SRC/config/$EDITION"; do
	[ -d "$d" ] && cp -a "$d/." config/
done
# Local apt repository of the TetronOS debs, served on 127.0.0.1 only while
# live-build runs (config/common/archives/tetronos-local.list.chroot).
REPO="$WORK/repo"
rm -rf "$REPO"; mkdir -p "$REPO"
ls "$SRC"/packaging/out/*.deb >/dev/null 2>&1 || { echo "no debs in packaging/out; run: make debs" >&2; exit 1; }
cp "$SRC"/packaging/out/*.deb "$REPO/"
(cd "$REPO" && apt-ftparchive packages . > Packages && apt-ftparchive release . > Release)
python3 -m http.server 8099 --bind 127.0.0.1 --directory "$REPO" >"$WORK/repo-http.log" 2>&1 &
HTTP_PID=$!
trap 'kill $HTTP_PID 2>/dev/null || true' EXIT
sleep 1
# The image installs no Recommends: the desktop gets the tools tetron-wm
# features use from the Recommends of the tetron-wm-desktop deb.
if [ "$EDITION" = desktop ]; then
	WMD=$(ls "$REPO"/tetron-wm-desktop_*_all.deb | head -1)
	dpkg-deb -f "$WMD" Recommends | tr ',' '\n' | sed 's/|.*//; s/(.*)//; s/ //g' | grep . \
		> config/package-lists/tetron-wm-desktop-tools.list.chroot
fi
export EDITION FIRMWARE
# Drop stage stamps, chroot and binary of an earlier build (the download cache stays).
lb clean
lb config
lb build
kill $HTTP_PID 2>/dev/null || true
python3 "$SRC/scripts/no_gui_check.py" binary/live/filesystem.packages "$SRC/config/gui-allowlist.txt"
mkdir -p "$OUTDIR"
ISO=$(ls -1 live-image-*.iso | head -1)
OUT="$OUTDIR/tetronos-$EDITION$SUFFIX-$(date +%Y%m%d)-amd64.iso"
cp "$ISO" "$OUT"
cp binary/live/filesystem.packages "${OUT%.iso}.packages"
ls -l "$OUT"
chown -R "${HOST_UID:-0}:${HOST_GID:-0}" "$OUTDIR" "$WORK"
