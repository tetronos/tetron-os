# ISO sizes

Server edition target: 300 MB (fungible, not a gate).

| Date | Build | ISO | squashfs | initrd | Note |
|---|---|---|---|---|---|
| 2026-10-26 | M0, `--firmware-chroot true` | 811 MB | 666 MB | 118 MB | all firmware packages pulled in (851 MB firmware) |
| 2026-10-26 | M0, `--firmware-chroot false` | 270 MB | 202 MB | n/a | bare: kernel, live-boot, systemd only |
| 2026-11-02 | M2, tetronos-live-config (kmscon, tetron suite) | 368 MB | 300 MB | 42 MB | over target: kmscon pulls the mesa GL stack (libllvm19 127 MB, mesa-libgallium 42 MB, libz3-4 27 MB installed); tetron 29 MB. M3 candidates |
