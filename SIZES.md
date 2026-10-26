# ISO sizes

Server edition budget: 300 MB.

| Date | Build | ISO | squashfs | initrd | Note |
|---|---|---|---|---|---|
| 2026-10-26 | M0, `--firmware-chroot true` | 811 MB | 666 MB | 118 MB | all firmware packages pulled in (851 MB firmware) |
| 2026-10-26 | M0, `--firmware-chroot false` | 270 MB | 202 MB | n/a | bare: kernel, live-boot, systemd only |
