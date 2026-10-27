#!/bin/sh
# Runs inside the build environment (VM or container). Assembles config/common + config/$EDITION
# into /build/$EDITION and runs live-build there.
set -e
EDITION="${EDITION:-server}"
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
export EDITION
lb config
lb build
mkdir -p "$OUTDIR"
ISO=$(ls -1 live-image-*.iso | head -1)
OUT="$OUTDIR/tetronos-$EDITION-$(date +%Y%m%d)-amd64.iso"
cp "$ISO" "$OUT"
cp binary/live/filesystem.packages "${OUT%.iso}.packages"
ls -l "$OUT"
chown -R "${HOST_UID:-0}:${HOST_GID:-0}" "$OUTDIR" "$WORK"
