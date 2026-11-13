# TetronOS

**Website: [tetronos.github.io/tetron-os](https://tetronos.github.io/tetron-os/)**

A GUI-less Debian trixie live ISO and installer. kmscon console, tetron-wm desktop, tetron mesh. No X11, no Wayland.

Editions are levels of one tree: `server` (ssh, no firmware) and `desktop` (hardware, sound, wifi, all firmware); `minimal` and `full` come later. `FIRMWARE=none|all` is a separate axis; `-fw` in the ISO name marks all firmware.

## Build

Default runner is a Debian 13 build VM (QEMU/KVM). `make vm-create` once, then `make iso`. `RUNNER=docker` uses a privileged trixie container instead.

    make vm-create
    make iso EDITION=server      # output in out/
    make iso EDITION=desktop     # tetronos-desktop-fw-*.iso

Each `make iso` also writes its full output to `out/logs/make-iso-<edition>[-fw]-<time>.log`.

## Layout

- `builder/`   Dockerfile for the build container
- `auto/`      live-build config, build, clean wrappers
- `config/common/`, `config/<edition>/`   live-build config overlaid per edition
- `scripts/`   build driver
- `tests/`     VM tests (QEMU)

Design and plans are kept locally, not in git.
