#!/bin/sh
# Runs inside a fresh debian:trixie container (packaging/build.py kind = "source"): builds kmscon
# without its OpenGL modules (video_drm3d, renderer_gltex), with touchpad tap-to-click, from the trixie-backports source and
# copies the deb to /out. The stock kmscon depends on libgbm1, which pulls mesa and LLVM (about
# 195 MB installed); this one needs none of them. tetron-wm never uses OpenGL, kmscon only renders
# its terminal, and kmscon uses its software renderer unless started with --hwaccel (default off,
# TetronOS never turns it on). Mounts: /src (this directory, read-only), /out. Env: VERSION
# (the full deb version, for example 10.0.4-1~bpo13+1tetronos1).
set -e
export DEBIAN_FRONTEND=noninteractive
: "${VERSION:?VERSION is required}"
sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/debian.sources
cat > /etc/apt/sources.list.d/backports.sources <<'EOF'
Types: deb deb-src
URIs: http://deb.debian.org/debian
Suites: trixie-backports
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF
apt-get -qq update
apt-get -qq install -y dpkg-dev devscripts fakeroot ca-certificates >/dev/null
mkdir /w && cd /w
apt-get -qq source -t trixie-backports kmscon >/dev/null
cd kmscon-*/
apt-get -qq build-dep -y -t trixie-backports kmscon >/dev/null
patch -p1 < /src/nogl-rules.patch
# Our patches to the source (packaging/kmscon/patches/, in order): touchpad tap-to-click.
for p in /src/patches/*.patch; do patch -p1 < "$p"; done
# TetronOS turns tapping on: the example config is what the package installs as /etc/kmscon/kmscon.conf.
sed -i 's/^#touchpad-tap$/touchpad-tap/' scripts/etc/kmscon.conf.example
grep -q '^touchpad-tap$' scripts/etc/kmscon.conf.example
DEBFULLNAME=TetronOS DEBEMAIL=noreply@tetron.invalid dch -v "$VERSION" -D trixie-backports \
	"Built without the OpenGL video and renderer modules (video_drm3d, renderer_gltex): no libgbm, mesa or LLVM dependency. Touchpad tap-to-click (--touchpad-tap), on by default in /etc/kmscon/kmscon.conf."
DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -us -uc -b >/tmp/kmscon-build.log 2>&1 || { tail -30 /tmp/kmscon-build.log; exit 1; }
cd ..
deb=$(ls kmscon_*_amd64.deb)
dpkg-deb -f "$deb" Depends | grep -qE "libgbm|libegl|libgles" && { echo "GL dependency still present" >&2; exit 1; }
cp "$deb" /out/
ls -l /out
