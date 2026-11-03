from libspec import Requirement


class OneTree(Requirement):
    """One source tree, one installer, one test harness for all editions.
    Editions differ only in package lists, firmware lists, boot entries, size
    budget and metapackage choice (EDITION). No edition-specific code paths in
    tetron-install."""


class NoGui(Requirement):
    """No graphical session, in any edition, on the live medium or the
    installed system: no X server, no Wayland compositor, no display
    manager, no desktop environment, no GUI installer. The user works in
    the terminal (kmscon plus tetron-wm). An app that also has a GUI is
    allowed when it is useful from the terminal, through a TUI, a CLI or a
    headless mode (for example keepassxc-cli, mpv on the framebuffer), and
    its packages do not pull in a graphical session. Library-level
    dependencies such as X11 or Wayland client libraries are tracked in
    config/gui-allowlist.txt. The build and the VM tests enforce this."""


class RegularNotBlocked(Requirement):
    """Server work must never block the desktop and full editions (the plan's
    Regular edition, split into desktop and full).
    Package lists are split by edition, tetronos-suite is a real metapackage
    from the start, kernel and firmware pruning is Server-only, both console
    paths (VGA kmscon and serial) work in both editions, the installer
    supports offline and network package sources, size budget and firmware
    set are configuration, not code."""


class NoSecretsInImage(Requirement):
    """No secrets, invite keys, ssh keys or tetron identity are baked into the
    ISO, a package, or the repo. Invites are delivered at runtime."""


class UniqueIdentityPerInstall(Requirement):
    """Every installed system has its own tetron node identity, ssh host keys
    and machine-id, generated at first boot. Two installs from the same ISO
    never share them."""


class SoftwareViaDebs(Requirement):
    """All non-Debian software (tetron suite, tetron-wm, fonts, later
    carbonyl and fresh) enters the image as .deb packages built by
    packaging/ from pinned, checksum-verified inputs. No curl-from-GitHub in
    hooks."""


class ReproducibleBuild(Requirement):
    """A fresh clone builds the ISO with make iso. Inputs are pinned (package
    versions, release tags and checksums). The build runs in a Debian 13
    environment (VM by default, container optional) and is runner-agnostic."""


class VmFirstHardwareAfter(Requirement):
    """Everything is validated in QEMU/KVM VMs before any real hardware. Real
    hardware validation (pizzabox via BMC virtual media) starts only after
    the VM acceptance suite passes."""


class BmcFriendlyServer(Requirement):
    """The Server ISO is as small as practical, boots as a CD-ROM (not only
    USB hybrid), has serial and VGA console entries, installs unattended, and
    the installer TUI works keyboard-only at 16 colors on a serial console."""


class ServerSizeBudget(Requirement):
    """The Server ISO targets 300 MB. The target is fungible, not a gate:
    no function is dropped to meet it without USER approval. Every built
    size is recorded in SIZES.md; when over the target, with the top
    packages and next steps."""


class InstallerSafety(Requirement):
    """tetron-install never touches a disk before an explicit confirm screen
    showing disk, size, model and the planned layout, refuses the live
    medium as a target, logs every step, and unwinds mounts and mappings on
    abort."""


class InstallModes(Requirement):
    """Install mode asks only disk, confirm, username, password and hostname,
    everything else fixed. Expert mode exposes partitioning, LUKS, LVM,
    filesystem, locale, keyboard, timezone, mirrors and extra packages."""


class BrandedBoot(Requirement):
    """A shipped ISO shows TetronOS branding, not Debian's: its own logo on
    the boot menu splash (syslinux on BIOS, grub on UEFI) and a TetronOS
    boot menu title, and TetronOS greeting text in /etc/issue, the motd
    and the kmscon login banner. Logo art and wording are USER decisions.
    Required before the release candidate (M8)."""


class EditionsAndFirmwareAxis(Requirement):
    """Editions are levels of one tree: server and desktop now, minimal and
    full later (core < server < desktop < full). EDITION selects the level.
    Firmware is a second, independent axis: FIRMWARE=none|all, default
    none for server and all for desktop. --firmware-chroot follows
    FIRMWARE. The ISO is named tetronos-<edition>[-fw]-<date>-amd64.iso,
    with -fw whenever FIRMWARE=all."""
