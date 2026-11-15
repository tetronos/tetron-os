#!/bin/sh
# Build kmscon without its OpenGL modules (video_drm3d, renderer_gltex) from the
# trixie-backports source, in the build VM, and put the deb in packaging/extra/.
# The stock kmscon depends on libgbm1, which pulls mesa and LLVM (about 195 MB
# installed); this one draws with the software path and needs none of them.
# tetron-wm never uses OpenGL, kmscon only renders its terminal. A test candidate
# (see the plan: hardware speed gate): use it with
#   make iso EDITION=server TAG=nogl
# Version 10.0.4-1~bpo13+1tetronos1 sorts above the backports 10.0.4-1~bpo13+1.
# Usage: packaging/kmscon/build-nogl.sh   (run from anywhere; needs the build VM)
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VM="$ROOT/scripts/vm.sh"
OUT="$ROOT/packaging/extra"
mkdir -p "$OUT"
"$VM" start
"$VM" sync
"$VM" ssh 'set -e
sudo apt-get install -y -q dpkg-dev devscripts fakeroot >/dev/null
rm -rf ~/kms && mkdir ~/kms && cd ~/kms
apt-get source -t trixie-backports kmscon >/dev/null 2>&1
cd kmscon-*/
sudo apt-get build-dep -y -q -t trixie-backports kmscon >/dev/null
patch -p1 < ~/src/packaging/kmscon/nogl-rules.patch
DEBFULLNAME=TetronOS DEBEMAIL=noreply@tetron.invalid dch -v 10.0.4-1~bpo13+1tetronos1 -D trixie-backports "Built without the OpenGL video and renderer modules (video_drm3d, renderer_gltex): no libgbm, mesa or LLVM dependency." >/dev/null 2>&1
DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -us -uc -b >/tmp/kmscon-build.log 2>&1 || { tail -20 /tmp/kmscon-build.log; exit 1; }
cd ..
dpkg-deb -f kmscon_*_amd64.deb Depends | grep -qE "libgbm|libegl|libgles" && { echo "GL dependency still present" >&2; exit 1; }
ls kmscon_*_amd64.deb'
f=$("$VM" ssh 'ls ~/kms/kmscon_*_amd64.deb' | tail -1)
"$VM" ssh "cat $f" > "$OUT/$(basename "$f")"
sha256sum "$OUT/$(basename "$f")"
ls -l "$OUT/$(basename "$f")"
