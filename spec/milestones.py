from libspec import Requirement


class M0RepoAndBuildHost(Requirement):
    """Milestone M0 acceptance: make iso EDITION=server completes on a clean
    Debian 13 host (build VM)."""


class M1Packages(Requirement):
    """Milestone M1 acceptance: Every tetron suite component and addon has a
    .deb that installs cleanly in a debian:trixie container; metapackages
    tetronos-core and tetronos-suite exist. tetronos-live-config (live
    autologin and sudo) is part of M2, because it depends on the console
    stack that M2 settles."""


class M2BareLiveIso(Requirement):
    """Milestone M2 acceptance: make iso builds the debs, installs
    tetronos-live-config (and through it tetronos-core) from the local apt
    repository, and produces an ISO that tests/boot-live.sh boots in QEMU
    BIOS and UEFI to tetron-wm on VGA (screenshot) and to a login prompt on
    serial (serial log); the build no-GUI check passes; the first size is recorded
    in SIZES.md."""


class M3SizePass(Requirement):
    """Milestone M3 acceptance: Server ISO is within the 300 MB budget or the
    gap is documented with the top 30 packages by size."""


class M4VmHarness(Requirement):
    """Milestone M4 acceptance: make test-live boots the ISO in BIOS and UEFI
    VMs and passes live assertions over ssh; the harness takes EDITION."""


class M5InstallerCore(Requirement):
    """Milestone M5 acceptance: make test-install performs an unattended
    install to an empty virtual disk (BIOS and UEFI), reboots from disk and
    passes ssh assertions; the live medium is refused as a target."""


class M6FirstBootIdentity(Requirement):
    """Milestone M6 acceptance: Two installs from one ISO have different tetron
    node IDs, ssh host keys and machine-ids; the tetron daemon starts;
    tetron join works against a test network."""


class M7InstallTui(Requirement):
    """Milestone M7 acceptance: The ratatui Install mode completes an install
    by hand on VGA and on serial in both firmware modes."""


class M8ReleaseCandidate(Requirement):
    """Milestone M8 acceptance: A fresh clone builds the ISO in CI and the VM
    acceptance suite passes; tag v1.0.0-rc1; checksums and signature
    published."""


class M9ServerHardware(Requirement):
    """Milestone M9 acceptance: The same ISO installs on a real server through BMC
    virtual media; consoles via BMC KVM, Serial-over-LAN and tetron work;
    the installed system has a unique identity, joins the mesh and powers
    off via BMC; findings in a HARDWARE_ notes file; tag v1.0.0."""


class R0RegularLists(Requirement):
    """Milestone R0 acceptance: make iso EDITION=full builds and make test-
    live EDITION=full passes (the plan's Regular edition, now the full
    level above desktop)."""


class R1CarbonylAndFresh(Requirement):
    """Milestone R1 acceptance: carbonyl and fresh are .debs and run in a
    tetron-wm window in a VM; carbonyl loads a page with truecolor and
    mouse."""


class R2FullSuiteValidation(Requirement):
    """Milestone R2 acceptance: Every suite app starts and works in the VM;
    glyphs and fonts render on kmscon; power actions work."""


class R3RegularInstallAndHardware(Requirement):
    """Milestone R3 acceptance: Regular installs in BIOS and UEFI VMs and on
    a real server via BMC; tag v1.1.0."""


class P0PackagingSkeleton(Requirement):
    """Milestone P0 acceptance: packaging/ manifest and build.sh produce a
    tetron-tui .deb that installs and runs in a trixie container."""


class P1ReleaseBinaryDebs(Requirement):
    """Milestone P1 acceptance: debs for tetron, tetron-wm, tetron-webui,
    tetron-messageboard and tetron-sync-receiver install, --version works,
    and unit files pass systemd-analyze verify."""


class P2SourceAndScriptDebs(Requirement):
    """Milestone P2 acceptance: debs for tetron-hosts, tetron-relay (once
    tested), tetron-backup and symbols-nerd-font install and smoke-test."""


class P3Metapackages(Requirement):
    """Milestone P3 acceptance: apt install of tetronos-core pulls every
    Depends in a trixie container."""


class P4IsoIntegration(Requirement):
    """Milestone P4 acceptance: make iso builds the debs and installs tetronos-
    core and tetronos-live-config into the ISO; dpkg -l in the chroot lists
    them."""



class D1DesktopIso(Requirement):
    """Milestone D1 acceptance: make iso EDITION=desktop builds
    tetronos-desktop-fw-*.iso with all firmware; tests/boot-live.sh boots it
    in BIOS and UEFI to tetron-wm; in the VM the live user can list and
    change NetworkManager connections without sudo (nmcli), sees a
    pipewire audio sink on an emulated sound card, and sshd is not
    running; the build no-GUI check passes; the size is recorded. Then a
    live boot on a test laptop (wifi, sound) by USER."""
