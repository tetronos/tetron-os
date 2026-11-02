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
    """tests/boot-live.sh ISO [bios|uefi] boots the ISO in QEMU/KVM with
    virtio-gpu and the serial port logged to a file, waits for boot, saves
    a VGA screenshot over QMP and powers the VM off. It passes when the
    serial log shows a shell prompt of user tetron and the screenshot shows
    tetron-wm (checked by eye in M2, automated in M4). Results go to
    out/boot-<firmware>.{log,png}."""
