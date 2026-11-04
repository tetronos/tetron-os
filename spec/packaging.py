from libspec import Requirement


class TetronDeb(Requirement):
    """The tetron core daemon and CLI come from the .deb that the tetron
    repository publishes with each release (tetron_<version>-<rev>_amd64.deb),
    pinned in the manifest and checksum verified. TetronOS does not rebuild
    it. Installs /usr/bin/tetron. The package version is the upstream
    version with a Debian revision (for example 0.15.0-1)."""


class TetronDebUnit(Requirement):
    """The tetron deb ships its own /usr/lib/systemd/system/tetron.service
    with ExecStart=/usr/bin/tetron daemon and no install-time placeholders.
    The package does not enable or start the service. The ISO build hook
    enables it."""


class TetronDebNoIdentity(Requirement):
    """No maintainer script and no build step starts the tetron daemon or
    creates /etc/tetron/secret_key. The tetron identity is created on first
    daemon start on the target machine. Purge keeps /etc/tetron so an
    identity is never deleted by a package operation."""


class TetronDebGroup(Requirement):
    """The tetron deb postinst creates the tetron system group idempotently
    (groupadd --system tetron, from the essential passwd package; addgroup is not guaranteed on minimal images), so /etc/tetron is created root:tetron by the
    daemon. The package depends on iproute2, which the daemon calls (ip) to
    configure the TUN link."""


class TetronDebSmokeTest(Requirement):
    """packaging/tests installs the tetron deb in a clean debian:trixie
    container, checks the file list, and verifies that tetron --version
    reports the package version. The unit passes systemd-analyze verify."""


class TetronFirstBootOperator(Requirement):
    """On first boot, after the tetron daemon is running, the primary user
    (uid 1000) is made the tetron operator (tetron set-operator USER) so the
    user can run tetron without sudo. Done by a oneshot unit in tetronos-core
    that disables itself afterwards."""


class PackagingManifest(Requirement):
    """packaging/manifest.toml is the single source of truth for every
    package: name, version, Debian revision, architecture, description,
    license, homepage, depends, source (release asset URL plus sha256 or a
    sha256 URL), installed files with modes, and maintainer scripts. A
    package whose upstream publishes a .deb uses kind = "deb" instead: name,
    version, revision, architecture, smoke command and the release .deb URL
    with its sha256 URL; files, scripts and control fields then come from
    that deb. Nothing is built from an unpinned or unverified input."""


class PackagingVerifiesChecksum(Requirement):
    """The build downloads each release asset into packaging/cache/, verifies
    its sha256 against the published checksum, and aborts with a clear error
    on mismatch. A cached file is re-verified before use."""


class PackagingUsesDpkgDeb(Requirement):
    """Packages are assembled with dpkg-deb --build --root-owner-group (no
    extra tooling such as fpm), so the build needs only python3 (stdlib) and
    dpkg. Files are owned by root, mtimes are clamped to SOURCE_DATE_EPOCH,
    and the same inputs produce the same package."""


class PackagingRunsAnywhere(Requirement):
    """packaging/build.py runs on any host with python3 and dpkg-deb (the
    Ubuntu dev host, the Debian 13 build VM, or CI) and writes debs to
    packaging/out/. It is not tied to the live-build environment."""


class PackagingTestsInCleanTrixie(Requirement):
    """packaging/tests/test-debs.sh installs each built deb in a fresh
    debian:trixie container using apt (so Depends resolve), checks the file
    list and modes, runs the smoke command, verifies unit files with
    systemd-analyze, then removes and purges the package cleanly."""


class PackagingConsumesReleaseDebs(Requirement):
    """For a kind = "deb" package, packaging/build.py downloads the release
    .deb into packaging/cache/, verifies its sha256, checks that its Package,
    Version and Architecture fields equal the manifest's name,
    version-revision and arch, aborts on any mismatch, and copies the deb
    unchanged to packaging/out/ as <name>_<version>-<revision>_<arch>.deb.
    The upstream deb is never unpacked or rebuilt."""


class SuiteDebsFromReleases(Requirement):
    """The manifest takes tetron, tetron-tui, tetron-wm, tetron-wm-desktop,
    tetron-wm-extras, tetron-webui and tetron-messageboard from their
    published release debs, all at the same tetron minor. tetron-wm-desktop
    and tetron-wm-extras are Architecture: all metapackages; packaging/tests
    installs them without Recommends."""


class MetapackagesBuiltHere(Requirement):
    """A kind = "meta" manifest entry is a metapackage built by
    packaging/build.py from the manifest alone: Architecture all, no
    download, Depends and Recommends taken from the entry, and no payload
    except /usr/share/doc/<name>/copyright, which states that the package
    has no content of its own. Its version is the tetron minor release the
    image tracks, with a Debian revision (for example 0.15.0-1). It is
    reproducible like every other package built here."""


class TetronosCoreMeta(Requirement):
    """tetronos-core is the base package set of every edition: it Depends on
    tetron, tetron-tui, tetron-wm, tetronos-branding, network-manager and kmscon (>= 10),
    which brings libtsm4 (>= 4.8) with it. openssh-server is not in core:
    it comes with tetronos-server. Both come from
    trixie-backports (see KmsconFromBackports). It does not pull
    tetron-wm-desktop, so Recommends of the desktop app list never reach
    the Server image. The symbols font and tetron-install are added when
    they have packages (M5)."""


class TetronosSuiteMeta(Requirement):
    """tetronos-suite is the full suite: it Depends on tetronos-core,
    tetron-wm-extras (which pulls tetron-wm-desktop and its app list as
    Recommends), tetron-webui and tetron-messageboard. tetron-sync-receiver
    and tetron-scripts are added when they publish release debs.
    tetron-hosts and tetron-systray are not part of it."""


class MetapackagesInstallFromRepo(Requirement):
    """packaging/tests builds a local apt repository from packaging/out/ in
    a fresh debian:trixie container, installs tetronos-suite from it without
    Recommends, and checks that every package named in the Depends of
    tetronos-core and tetronos-suite is installed. Removing tetronos-suite
    and tetronos-core then removes no other package."""


class KmsconFromBackports(Requirement):
    """kmscon 10 and libtsm4 4.8 exist only in trixie-backports. TetronOS
    enables trixie-backports with an apt pin that raises only kmscon and
    libtsm4 (priority 600) and leaves every other backports package at 100,
    so nothing else is taken from backports. The ISO build uses the pin in
    the chroot and ships it in the image (binary). packaging/tests enables
    the same source and pin in the container before installing the
    metapackages."""


class LocalPackagesBuiltHere(Requirement):
    """A kind = "local" manifest entry is a package built by
    packaging/build.py from files tracked in this repository
    (packaging/files/<name>/), with modes and maintainer scripts taken from
    the entry. Nothing is downloaded; the inputs are pinned by the
    repository commit. It is reproducible like every other package built
    here. Its copyright file states that it is TetronOS configuration."""


class TetronosLiveConfig(Requirement):
    """tetronos-live-config turns the live medium into a console that boots
    to tetron-wm. It is installed only in the ISO, never by tetronos-core
    or tetronos-suite. It Depends on tetronos-core, live-boot, live-config,
    live-config-systemd, user-setup (live-config creates the live user only
    with it, and the image installs no Recommends), sudo and
    fonts-dejavu-core, and ships:
    a kmsconvt@tty1 drop-in in /usr/lib/systemd/system that runs kmscon
    on tty1 with DejaVu Sans Mono 14, us keyboard, mouse on, and agetty
    autologin of the live user tetronos with TERM xterm-256color; /usr/bin/tetron-session,
    which attaches to a running tetron-wm session (tetron-wm attach -d) or
    starts one, and falls back to a login shell when tetron-wm is missing;
    /etc/profile.d/tetronos-session.sh, which runs tetron-session only in a
    login shell under kmscon or on tty1, never over ssh, never inside
    tetron-wm. Its postinst enables kmsconvt@tty1 and disables getty@tty1;
    removing the package reverts both. The live user tetronos and its
    passwordless sudo come from live-config (username=tetronos on the
    kernel command line). The user is not named tetron: that name is the
    tetron daemon's system group, and adduser can not create a user whose
    own group already exists. The serial console shows a login prompt (no autologin)."""


class TetronosServerMeta(Requirement):
    """tetronos-server is the Server edition package set: it Depends on
    tetronos-core (same version), openssh-server, python3 and python3-apt.
    The Server ISO keeps sshd enabled. python3 is there because users
    expect Ansible to manage a server, and Ansible needs python3 on the
    managed node; python3-apt is what Ansible's apt module uses."""


class TetronosDesktopMeta(Requirement):
    """tetronos-desktop is the Desktop edition package set, the level above
    server (core < server < desktop < full): it Depends on tetronos-server
    (same version), tetronos-desktop-config, tetron-wm-desktop, polkitd,
    libpam-systemd and dbus-user-session (a logind session and a user bus
    for the console login), wpasupplicant, wireless-regdb, iw, pipewire,
    pipewire-alsa, pipewire-pulse, wireplumber, alsa-utils, bluez,
    brightnessctl, upower, intel-microcode and amd64-microcode. Installing
    it on a server with apt (Recommends on) also brings the tetron-wm-desktop
    tools."""


class TetronosDesktopConfig(Requirement):
    """tetronos-desktop-config (kind local) ships polkit rules in
    /usr/share/polkit-1/rules.d/ that let members of netdev manage
    NetworkManager and members of users power off, reboot, suspend and
    hibernate. kmscon runs the login on a pts, so the session is not an
    active seat session and polkit's allow_active defaults do not apply.
    Bluetooth access comes from bluez's own D-Bus policy for the bluetooth
    group."""


class TetronosBranding(Requirement):
    """tetronos-branding (kind local) gives every TetronOS system, live or
    installed, TetronOS greeting text. It ships issue, issue.net and motd in
    /usr/share/tetronos-branding/. Its postinst diverts /etc/issue,
    /etc/issue.net and /etc/motd from base-files to <file>.debian with
    dpkg-divert --rename and points each at its TetronOS copy with a
    symlink, so base-files upgrades never overwrite them. /etc/issue names
    the base with agetty's \\S{PRETTY_NAME}, so it stays right across
    Debian releases. A file the admin put in place of a symlink is kept.
    Removing the package removes its symlinks and restores the Debian
    files."""
