# TetronOS

A GUI-less Debian trixie live ISO and installer. kmscon console, tetron-wm desktop, tetron mesh. No X11, no Wayland.

Editions: `server` (minimum size, built and tested first) and `regular` (everything rolled in).

## Build

Default runner is a Debian 13 build VM (QEMU/KVM). `make vm-create` once, then `make iso`. `RUNNER=docker` uses a privileged trixie container instead.

    make vm-create
    make iso EDITION=server      # output in out/

## Layout

- `builder/`   Dockerfile for the build container
- `auto/`      live-build config, build, clean wrappers
- `config/common/`, `config/<edition>/`   live-build config overlaid per edition
- `scripts/`   build driver
- `tests/`     VM tests (QEMU)

Design and plans are kept locally, not in git.
