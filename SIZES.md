# ISO sizes

Server edition target: 300 MB (fungible, not a gate).

| Date | Build | ISO | squashfs | initrd | Note |
|---|---|---|---|---|---|
| 2026-10-26 | M0, `--firmware-chroot true` | 811 MB | 666 MB | 118 MB | all firmware packages pulled in (851 MB firmware) |
| 2026-10-26 | M0, `--firmware-chroot false` | 270 MB | 202 MB | n/a | bare: kernel, live-boot, systemd only |
| 2026-11-02 | M2, tetronos-live-config (kmscon, tetron suite) | 368 MB | 300 MB | 42 MB | over target: kmscon pulls the mesa GL stack (libllvm19 127 MB, mesa-libgallium 42 MB, libz3-4 27 MB installed); tetron 29 MB. M3 candidates |
| 2026-11-03 | D1 desktop, FIRMWARE=all (`tetronos-desktop-fw`) | 1040 MB | n/a | n/a | 553 packages, 33 firmware packages (about 540 MB of the size, see M0 row); target fungible, no target set for desktop |
| 2026-11-04 | server + python3, python3-apt (Ansible) and tetronos-branding | 375 MB | n/a | n/a | +7.3 MB over the 2026-11-03 server ISO (368,050,176 to 375,390,208 bytes); Ansible ping, facts and apt module pass against the live VM |
| 2026-11-08 | server, tetron 0.15.3, tetron-wm 0.15.5 | 377 MB | n/a | n/a | +2.1 MB over the 2026-11-04 server ISO (375,390,208 to 377,487,360 bytes), from newer tetron suite packages |
| 2026-11-09 | server, tetron-wm 0.15.6 (local debs), tetronos-core 0.15.0-7 with tetronos-nerd-font-symbols | 381 MB | n/a | n/a | +3.1 MB over the 2026-11-08 server ISO (377,487,360 to 380,633,088 bytes), mostly the symbols Nerd Font now in tetronos-core |
