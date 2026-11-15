#!/bin/sh
# kmscon without OpenGL is a package of the manifest now (kind = "source", built by
# packaging/build.py in a debian:trixie container with packaging/kmscon/build-in-container.sh).
# This wrapper only builds it on its own, into packaging/extra/ (for a TAG= test build):
#   packaging/kmscon/build-nogl.sh
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$ROOT/packaging/build.py" --only kmscon --out "$ROOT/packaging/extra"
