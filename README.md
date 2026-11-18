# TetronOS

**Website: [tetronos.github.io/tetron-os](https://tetronos.github.io/tetron-os/)**

A GUI-less Debian trixie live ISO and installer. kmscon console, tetron-wm desktop, tetron mesh. No X11, no Wayland.

Editions are levels of one tree: `server` (ssh, no firmware) and `desktop` (hardware, sound, all firmware; the server has wifi firmware too, `FIRMWARE=all` adds the rest); `minimal` and `full` come later. `FIRMWARE=none|all` is a separate axis; `-fw` in the ISO name marks all firmware.

## Create an ISO: walkthrough

This walkthrough takes a fresh Debian or Ubuntu machine to a bootable TetronOS ISO. Run every command as your normal user from the `tetron-os` checkout; `sudo` is used only where shown. Three ISOs can be built:

| ISO | Command | Size | File name |
|---|---|---|---|
| server | `make iso EDITION=server` | ~515 MB | `tetronos-server-YYYYMMDD-amd64.iso` |
| server with all firmware | `make iso EDITION=server FIRMWARE=all` | ~910 MB | `tetronos-server-fw-YYYYMMDD-amd64.iso` |
| desktop | `make iso EDITION=desktop` | ~1.6 GB | `tetronos-desktop-YYYYMMDD-amd64.iso` |

The ISO is assembled from the released `.deb` files of the components (tetron, tetron-tui, tetron-wm and so on). They are downloaded during the build, so this one repository is all you need. The build itself runs inside a throwaway Debian 13 VM, so your own system stays untouched.

### 1. Install the host tools

You need an x86_64 Linux machine with about 40 GB free disk, 8 GB spare RAM and hardware virtualisation (KVM).

```sh
sudo apt update
sudo apt install git make python3 qemu-system-x86 qemu-utils xorriso rsync openssh-client curl cpu-checker docker.io
```

Docker builds kmscon, the console program, from its Debian source in a container (step 5).

### 2. Allow your user to use KVM and Docker

```sh
sudo usermod -aG kvm,docker $USER
```

Log out and in again, then confirm both groups are listed and KVM works. `kvm-ok` must print `KVM acceleration can be used`.

```sh
id -nG
kvm-ok
docker run --rm hello-world
```

If `kvm-ok` fails, enable VT-x or AMD-V in the firmware setup of the machine.

### 3. Get the repository

```sh
git clone https://github.com/tetronos/tetron-os
cd tetron-os
```

Already cloned? Bring it up to date:

```sh
git switch main
git pull --ff-only
```

Only `tetron-os` is cloned. The other components are not built here: the build downloads their released `.deb` files from GitHub, checks each against its published SHA-256, and uses it unchanged. No login is needed.

| Component | Comes from |
|---|---|
| tetron, tetron-tui, tetron-wm (+ `-desktop`, `-essentials`, `-recommended`, `-extras`), tetron-appstore, tetron-stt, tetron-aimode, tetron-browser | release `.deb` on `github.com/tetronos/<repo>/releases` |
| Nerd Font symbols | release zip on `github.com/ryanoasis/nerd-fonts` |
| kmscon | Debian source package, built here in a Docker container |
| `tetronos-*` (branding, base config, firstboot, apt source, metapackages, live config) | made here from `packaging/manifest.toml` and `packaging/files/` |
| everything else | the Debian trixie archive |

`packaging/manifest.toml` pins the exact version and URL of each one. You only clone a component repository when you change that component: build its `.deb` there, put it in a folder, and test it in the ISO with `make iso EDITION=server TAG=mytest LOCAL_DEBS=/path/to/folder`. A file in that folder replaces the download when it has the exact file name the manifest expects. This is for test builds only, never for a release.

### 4. Check the component versions (optional)

`packaging/manifest.toml` is the single list of every `.deb` the ISO is made from. `main` already pins tested versions, so you can skip this step. To see whether newer component releases exist (a line starting `DIFF` means a pin is behind):

```sh
python3 scripts/pins.py check
```

To take the newer releases, work on a branch, update the pins and commit:

```sh
git switch -c packaging/bump-components-$(date +%Y%m%d)
python3 scripts/pins.py update
git diff
git commit -am "packaging: the ISO takes the latest component releases"
```

### 5. Build and check the packages

This downloads every pinned `.deb`, verifies its checksum, builds the TetronOS metapackages and builds kmscon from source into `packaging/out/`. The first run takes a few minutes; kmscon is cached in `packaging/cache/source/` afterwards. A `HTTP Error 504` retry line is normal, GitHub is sometimes slow.

```sh
python3 packaging/build.py
python3 packaging/tests/test_build.py
python3 reconcile.py > /dev/null && echo rules ok
```

`make iso` runs the package build by itself as well, so this step is a check that fails fast and cheap before the long ISO build.

### 6. Create the build VM (once)

This downloads the Debian 13 cloud image, verifies its SHA-512 checksum, creates a 40 GB disk under `build/vm/` and installs live-build inside. It takes a few minutes and is needed only once.

```sh
make vm-create
```

The VM uses 6 CPUs, 8 GB RAM and ssh on port 2222 of localhost. Change these with environment variables if your machine needs it, for example:

```sh
VM_CPUS=4 VM_MEM=6G VM_PORT=2223 make vm-create
```

Use the same variables on every later `make` call. `make vm-start`, `make vm-stop` and `make vm-shell` start, stop and log into the VM by hand; `make iso` starts it by itself.

### 7. Build the ISO

Pick one:

```sh
make iso EDITION=server
make iso EDITION=server FIRMWARE=all
make iso EDITION=desktop
```

`make iso` starts the VM, copies the repository into it, runs live-build, and copies the result back to `out/`. The full output is also written to `out/logs/make-iso-<edition>[-fw]-<time>.log`; the path is printed at the start and the end. The build takes a while; the desktop edition is the longest.

A test build can carry a name so it does not mix with regular builds: `make iso EDITION=server TAG=mytest` gives `tetronos-server-mytest-YYYYMMDD-amd64.iso`.

An ISO with the same name is never overwritten; the older one is moved to `out/archive/` first.

### 8. Check the result

```sh
ls -lh out/*$(date +%Y%m%d)*
grep -E '^tetron' out/tetronos-server-$(date +%Y%m%d)-amd64.packages
sha256sum out/tetronos-server-$(date +%Y%m%d)-amd64.iso
```

The `.packages` file next to each ISO lists every package inside it. Replace `server` with `server-fw` or `desktop` as built.

### 9. Boot it in a VM first

Never try a new ISO on real hardware before it boots in a VM.

```sh
qemu-system-x86_64 -enable-kvm -m 4G -cdrom out/tetronos-server-$(date +%Y%m%d)-amd64.iso -boot d
```

To boot with UEFI instead of BIOS, install `ovmf` and add `-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd`. `tests/boot-live.sh` boots an ISO both ways.

### 10. Write it to a USB stick

Everything on the stick is lost. Find the stick with `lsblk` (compare the list before and after plugging it in) and replace `/dev/sdX` with the whole device, not a partition:

```sh
lsblk
sudo dd if=out/tetronos-server-$(date +%Y%m%d)-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

### All steps in one script

`scripts/roll-iso.sh` checks that the repository is clean and in sync, checks the pins, builds and tests the packages, creates the VM if missing and builds the ISOs. It stops at the first problem and never changes a pin for you.

```sh
scripts/roll-iso.sh                 # server, server-fw and desktop
scripts/roll-iso.sh server          # one ISO
scripts/roll-iso.sh server-fw desktop
```

### Without a VM: Docker runner

`RUNNER=docker` builds inside a privileged Debian trixie container instead of the VM. It skips step 6 but runs live-build with root privileges on your host kernel.

```sh
make iso EDITION=server RUNNER=docker
```

### Troubleshooting

Find the first real error in the newest log:

```sh
grep -nE '^E:' out/logs/$(ls -t out/logs | head -1)
```

- `Package X has no installation candidate`: a component now needs a package the manifest does not carry. Add a `[[package]]` block to `packaging/manifest.toml` by copying a neighbouring `kind = "deb"` block.
- `HTTP Error 504` that ends the build: run it again, GitHub can stay slow for a while.
- `rm: cannot remove 'chroot/dev/pts/...'` on the next build: a failed build left mounts in the VM. Unmount them and clear that edition's work folder (replace `desktop` as needed):

  ```sh
  scripts/vm.sh ssh 'mount | grep /var/tmp/build/desktop | awk "{print \$3}" | sort -r | while read m; do sudo umount -l "$m"; done'
  make clean EDITION=desktop
  ```

- The VM does not start: check `kvm-ok`, the `kvm` group, and that port 2222 is free (or set `VM_PORT`).
- `vm exists` on `make vm-create`: the VM is already there, go on with step 7. `make vm-destroy` stops it and deletes all of `build/vm/` (disk, cloud image, ssh key) if you really want a new one.
- Disk full: `scripts/out-report.sh out` shows sizes. Old ISOs in `out/archive/` can be removed by hand, nothing is deleted for you.

More detail on the manifest, pin rules and tier upgrades: [docs/HOWTO_TetronOS_roll_your_own_iso_server_and_desktop.md](docs/HOWTO_TetronOS_roll_your_own_iso_server_and_desktop.md).

## Layout

- `builder/`   Dockerfile for the build container
- `auto/`      live-build config, build, clean wrappers
- `config/common/`, `config/<edition>/`   live-build config overlaid per edition
- `packaging/` manifest and build of every `.deb` in the ISO
- `scripts/`   build driver, build VM, pins, roll-iso
- `tests/`     VM tests (QEMU)

Design and plans are kept locally, not in git.
