# HOWTO: roll your own TetronOS ISO

Each step is a short explanation followed by the command. Run everything from the `tetron-os` checkout unless a step says otherwise. Two editions exist: `server` (small, ssh, no firmware) and `desktop` (tetron-wm desktop, hardware support, firmware).

## 1. What you need

A Linux machine with about 40 GB free disk, 8 GB spare RAM, KVM, and these tools. The ISO is built inside a throwaway Debian 13 VM, so your own system stays untouched.

    sudo apt install git make python3 qemu-system-x86 qemu-utils genisoimage openssh-client curl

Check that KVM works (the command must print `KVM acceleration can be used`):

    sudo apt install cpu-checker && kvm-ok

## 2. Get the repositories

The ISO packages the released `.deb` files of the components, so the component repos are only needed to check versions. Put them all side by side in one folder, for example `~/code`.

    mkdir -p ~/code && cd ~/code
    for r in tetron-os tetron tetron-tui tetron-wm tetron-browser tetron-appstore tetron-packaging tetronos-apt; do git clone https://github.com/tetronos/$r; done

Already cloned? Update them instead:

    for r in tetron-os tetron tetron-tui tetron-wm tetron-browser tetron-appstore tetron-packaging tetronos-apt; do git -C ~/code/$r pull --ff-only; done

## 3. Check each repository is clean and in sync

A clean repo has nothing uncommitted. In sync means no commits ahead of or behind origin. Both counts must be `0`.

    cd ~/code/tetron-os
    git status -sb
    git fetch && git rev-list --left-right --count HEAD...@{u}

Do the same for any component with `git -C ~/code/tetron-wm status -sb`. Work on a branch, never directly on `main`:

    git switch -c packaging/bump-components-$(date +%Y%m%d)

## 4. Find the latest released version of each component

The ISO takes the newest published release of each component, tagged `vMAJOR.MINOR.PATCH`. The repos are public, so git can list the tags without any login. Pre-release tags (with a `-` suffix) are skipped.

    for r in tetron tetron-tui tetron-wm tetron-browser tetron-appstore; do echo "$r: $(git ls-remote --tags --refs https://github.com/tetronos/$r 'v[0-9]*' | sed 's#.*refs/tags/##' | grep -v -- '-' | sort -V | tail -1)"; done

## About the manifest

`packaging/manifest.toml` is the single list of every `.deb` the ISO is made from. Nothing else decides which version of a component goes in. Each package is one `[[package]]` block with a `kind` that says where it comes from.

- `kind = "deb"`: a component built and published by its own repo (tetron, tetron-tui, tetron-wm, tetron-browser, tetron-appstore). The block gives the release `url` and a `sha256_url`; the build downloads the file, checks the checksum and uses it unchanged.
- `kind = "meta"`: a metapackage made here from the block alone, no download. It only carries `depends` and a description, for example `tetronos-server` and `tetronos-suite`.
- `kind = "local"`: a package made here from the files under `packaging/files/<name>/`, for example `tetronos-branding` and `tetronos-live-config`.

The fields you will touch most:

- `version` and `revision`: the deb is `name_version-revision`. For a release deb the version is the release tag without the `v`, and the revision is almost always `1`.
- `url` and `sha256_url`: both contain the tag and the file name, so a version bump changes the `version` line and both URLs.
- `depends`: relations between packages built here. Write `"name (>= FLOOR)"` and `"name (<< NEXT_MINOR)"`, never `=`. The floor is the lowest revision that has what the dependent needs, the ceiling keeps one minor release (0.15.x) together.
- `smoke`: a command run after install to prove the binary works, for example `tetron --version`.

Rules to remember:

- A package built here (kind `meta` or `local`) gets a new `revision` with every change, because the apt repository holds one `.deb` per version.
- The tetron core and its add-ons use the same minor version (0.15.x). Upstream version numbers of other software do not matter.
- Check the pins in step 5 against the releases from step 4 before every build.
- Read the comment at the top of the manifest for the full rules, including `breaks` and `replaces` when a file moves between packages.

See what the manifest currently builds, without building:

    python3 packaging/build.py --list-debs

## 5. Check the pinned versions match

`packaging/manifest.toml` is the single list of which `.deb` goes into the ISO. Show what it pins:

    grep -E '^(name|version) =' packaging/manifest.toml | paste - - | grep -E 'tetron(-tui|-wm|-browser|-appstore)?"'

Compare each version with step 4. The `tetron-wm` family (`tetron-wm`, `-desktop`, `-essentials`, `-recommended`, `-extras`) must all carry the same version. Where a pin is old, change the version in its `version =` line and in both URLs of its `[package.source]` block (`url` and `sha256_url`). Example, tetron-wm 0.15.7 to 0.15.13 in one command:

    sed -i 's#tetron-wm/releases/download/v0.15.7#tetron-wm/releases/download/v0.15.13#; s#\(tetron-wm[a-z-]*\)_0.15.7-1#\1_0.15.13-1#' packaging/manifest.toml

Then fix the `version = "..."` lines of those entries by hand and review the change:

    git diff

If a new release adds a package the old one did not have, the build fails later with `has no installation candidate`. Add a `[[package]]` entry for it by copying a neighbouring `kind = "deb"` block, then continue. Commit the change on your branch:

    git commit -am "packaging: the ISO takes the latest component releases"

## 6. Check the packaging

This downloads every pinned `.deb`, verifies its checksum, and builds the TetronOS meta packages into `packaging/out/`. A `HTTP Error 504` retry line is normal, GitHub is sometimes slow.

    python3 packaging/build.py

Run the unit tests of the packaging code:

    python3 packaging/tests/test_build.py

Check the project rules (no GUI stack in the image, package relations, parity tables):

    python3 reconcile.py

Optional and slow, needs Docker: install the debs in a clean container and upgrade from the previous release. Run it before a public release.

    make test-debs

## 7. Create the build VM (once)

The VM is a Debian 13 image under QEMU. This step takes a few minutes and is only needed the first time.

    make vm-create

Check it starts and stop it again if you wish (`make iso` starts it by itself):

    make vm-start
    make vm-stop

## 8. Build the ISOs

The server ISO, about 380 MB. The finished file lands in `out/` and the full log in `out/logs/`.

    make iso EDITION=server

The desktop ISO, larger because it carries the desktop and firmware.

    make iso EDITION=desktop

The server edition with all firmware baked in, for real hardware (graphics, network cards, sound). The name carries `-fw`, `tetronos-server-fw-YYYYMMDD-amd64.iso`, and the ISO is about 910 MB. The plain server already has the wifi firmware and the wifi stack (`tetronos-firmware-wifi`), so a laptop with only wifi can get online. `FIRMWARE=all` adds the rest of the firmware (`tetronos-firmware`).

    make iso EDITION=server FIRMWARE=all

The desktop edition always has all firmware, so its name has no `-fw`: `tetronos-desktop-YYYYMMDD-amd64.iso`.

Same-name ISOs are never overwritten, the older one is moved to `out/archive/`.

## 9. Check the result

List the new files. The name carries the edition and the date, `tetronos-server-YYYYMMDD-amd64.iso`. The `.packages` file lists every package inside.

    ls -lh out/*$(date +%Y%m%d)*

Confirm the new versions are inside the ISO:

    grep -E '^tetron' out/tetronos-server-$(date +%Y%m%d)-amd64.packages

Write down a checksum to share with the ISO:

    sha256sum out/tetronos-server-$(date +%Y%m%d)-amd64.iso

## 10. Boot it

Try it in a VM first. Never test a new ISO on real hardware before it works in a VM.

    qemu-system-x86_64 -enable-kvm -m 4G -cdrom out/tetronos-server-$(date +%Y%m%d)-amd64.iso -boot d

To write it to a USB stick (replace `/dev/sdX` with the stick, check with `lsblk`, everything on it is lost):

    lsblk
    sudo dd if=out/tetronos-server-$(date +%Y%m%d)-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync

## 11. All of it in one script

`scripts/roll-iso.sh` runs steps 3 to 8 and stops at the first problem. It checks the repos are clean and in sync, checks every pin against the latest release tag, builds the debs, runs the tests, then builds the ISOs. It never changes a pin for you, a failed check prints what differs and you fix it as in step 5.

    scripts/roll-iso.sh                 # server and desktop
    scripts/roll-iso.sh server          # one edition
    CODE=$HOME/src scripts/roll-iso.sh  # repos live elsewhere

## Upgrade a running system to the next tier

The tiers are cumulative metapackages from the tetronos apt repository, so one command moves a system up. Server to server with firmware:

    sudo apt install tetronos-firmware

Server or server with firmware to desktop (adds the desktop, the browser, the app store, casttui, polkit, sound and the desktop defaults):

    sudo apt install tetronos-desktop

A running ssh server stays enabled during the upgrade, so a remote machine stays reachable.

## Troubleshooting

A build that fails prints the last lines of the log. Find the first real error in the full log:

    grep -nE '^E:' out/logs/$(ls -t out/logs | head -1)

- `Package X has no installation candidate`: a component now needs a package the manifest does not carry. See step 5.
- `HTTP Error 504` that ends the build: run it again, downloads are retried but GitHub can stay down for a while.
- `rm: cannot remove 'chroot/dev/pts/...': Operation not permitted` on the next build: the failed build left mounts in the VM. Unmount them and clear that edition's work folder (replace `desktop` as needed):

      scripts/vm.sh ssh 'mount | grep /var/tmp/build/desktop | awk "{print \$3}" | sort -r | while read m; do sudo umount -l "$m"; done'
      make clean EDITION=desktop

- `VM does not start`: check `kvm-ok` and that port 2222 is free, or set `VM_PORT=2223`.
- Disk full: `scripts/out-report.sh out` shows sizes. Old ISOs in `out/archive/` can be removed by hand, nothing is deleted for you.
