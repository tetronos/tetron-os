from libspec import Requirement


class IsoFromLocalAptRepo(Requirement):
    """make iso runs make debs first. scripts/build.sh turns packaging/out/
    into an apt repository (apt-ftparchive Packages and Release) and serves
    it over HTTP on 127.0.0.1 only while live-build runs. The chroot reads it
    through a chroot-only archive entry ([trusted=yes]), so neither the
    repository nor its sources entry is left in the image. The server
    package list installs tetronos-live-config from it."""


class TetronServiceEnabledInImage(Requirement):
    """A chroot hook enables tetron.service in the image. The tetron
    identity is still created on first daemon start on the booted system,
    never during the build."""


class NoGuiBuildCheck(Requirement):
    """scripts/no_gui_check.py reads an image package list and
    config/gui-allowlist.txt and reports every X server, Wayland
    compositor, display manager or desktop environment package that is not
    allowed. scripts/build.sh runs it on the built image and fails the
    build on any violation, before the ISO is copied to out/. reconcile.py
    (CON-T02) uses the same script."""


class LiveBootTest(Requirement):
    """tests/boot-live.sh ISO [bios|uefi] boots the ISO (any edition) in QEMU/KVM with
    virtio-gpu and the serial port logged to a file, waits for boot, saves
    a VGA screenshot over QMP and powers the VM off. It passes when the
    serial log shows the login prompt of host tetron and the screenshot
    shows tetron-wm (checked by eye in M2, automated in M4). Results go to
    out/boot-<firmware>.{log,png}."""


class DesktopToolsInImage(Requirement):
    """The image installs no Recommends, so for the desktop edition
    scripts/build.sh writes the Recommends of the tetron-wm-desktop,
    tetron-wm-essentials and tetron-wm-recommended debs (first choice of
    each alternative) into generated package lists. The tools and apps then
    always match the tetron-wm release in the manifest."""


class DesktopOpencodeInSkel(Requirement):
    """opencode, the agent of the tetron-wm Assistant, has no upstream
    package. A Desktop chroot hook installs it the way the tetron-wm suite
    installer does: upstream's latest stable release (x64-baseline, which
    runs on every x86_64 CPU), checked against the sha256 digest GitHub
    records for it, as /etc/skel/.local/bin/opencode. The live user and
    every user an install creates own a copy in ~/.local/bin, which
    Settings > Updates and opencode itself keep current without sudo. The
    build fails when the release or its digest can not be read."""


class AptRecommendsDefaultInImage(Requirement):
    """The image is built without Recommends (auto/config), but a running
    TetronOS, live or installed, installs Recommends like Debian: a chroot
    hook of every edition removes /etc/apt/apt.conf.d/00recommends, which
    live-build leaves in the image. The tetron-wm app sets are metapackages
    of Recommends and install nothing without them."""


class DesktopSshOff(Requirement):
    """The desktop edition installs openssh-server but a chroot hook
    disables ssh.service and ssh.socket, so a fresh desktop (live or
    installed from it) does not listen for ssh. A server upgraded to
    desktop keeps its sshd state."""
