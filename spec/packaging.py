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
    """tetronos-firstboot ships tetronos-firstboot.service (Type=oneshot) and
    /usr/libexec/tetronos/firstboot. The unit runs after tetron.service and
    live-config.service, once per system: it creates the stamp
    /var/lib/tetronos/firstboot.done and does not run while the stamp
    exists (on the live ISO the stamp lives in RAM, so it runs every live
    boot). The script waits up to 60 s for the tetron daemon to answer,
    then makes the primary user (the first /etc/passwd entry with a uid
    from 1000 to 59999: tetronos on the live ISO, the installed user on an
    installed system) the tetron operator with `tetron set-operator`, so
    that user can join, invite and leave without sudo. The daemon can answer
    `status` before it accepts `set-operator` (VM test 2026-11-05: it failed
    0.2 s after start), so set-operator is retried every 2 s for up to 60 s
    and its error text is logged when it still fails. If
    /etc/tetron/pending-invite exists (written 0600 by the installer, or
    dropped in by hand), it waits up to 60 s for the network
    (nm-online), runs `tetron join --invite-file /etc/tetron/pending-invite`
    and deletes the file whatever the result. The invite never appears in
    argv, the journal or a log; only the step names and outcomes are logged.
    Packages never enable units: the image enables it (live hook), the
    installer enables it on the target. tetronos-core Depends on it
    (USER 2026-11-04, join plan decisions 13 and 14)."""


class TetronosBaseConfig(Requirement):
    """tetronos-base-config (kind local) is the config every edition shares.
    Its postinst creates /etc/skel/Desktop, Documents, Downloads,
    Pictures and code (mode 0755), so every new user, the live user
    tetronos included, has the folders the tetron-wm Files app expects
    (USER 2026-11-03) and ~/code, the code and AI folder (USER 2026-11-15:
    it was not created on the server ISO). Its postrm on remove or purge deletes those folders only
    when they are empty. It also ships
    /usr/lib/sysctl.d/50-tetronos-ping.conf with
    `net.ipv4.ping_group_range = 0 2147483647`, so every user can ping
    through ICMP datagram sockets: the image loses ping's cap_net_raw file
    capability, and the kernel default range "1 0" allows nobody (VM test
    2026-11-05). This is the systemd upstream default. Its postinst makes
    multi-user.target the default boot target (symlink
    /etc/systemd/system/default.target): there is no display manager, the
    desktop starts after the kmscon login on tty1 (USER 2026-11-21); its
    postrm removes the symlink again when it still points there.
    tetronos-ssh-temp cleanup (run at boot by
    tetronos-ssh-temp-cleanup.service, Before=ssh.service) makes no systemctl
    or loginctl call: stopping or reloading ssh.service there waits for
    ssh.service's own start job, which waits for the cleanup, and the boot
    never finished (deadlock found 2026-11-21). The unit also has
    TimeoutStartSec=30.
    It ships /etc/apt/apt.conf.d/90tetronos-lean: Dir::Cache::pkgcache and
    srcpkgcache empty (no 49 MB cache file rewritten after every apt update)
    and Acquire::Languages none (no 35 MB translation index), because a
    USB stick writes 0.4 MB/s and apt install sat minutes in the cache
    rebuild (P1, 2026-11-21).
    tetronos-core Depends on it."""


class TetronosLiveSshPassword(Requirement):
    """On the live ISO, SSH password login is allowed only once no account
    has the public live password. live-config sets the live user's
    password to "live" (a DES crypt hash) and switches
    PasswordAuthentication off in /etc/ssh/sshd_config. tetronos-live-config
    ships /usr/libexec/tetronos/live-ssh-password, which checks every
    /etc/shadow hash against crypt("live") and writes
    /etc/ssh/sshd_config.d/40-tetronos-live-password.conf with
    PasswordAuthentication and KbdInteractiveAuthentication both "no"
    while any account still matches, and both "yes" once none does (the
    drop-in is read first, so it wins over the main file). It runs
    before sshd starts (ssh.service drop-in ExecStartPre) and whenever
    /etc/shadow changes (tetronos-live-ssh-password.path), then reloads ssh
    if it is running, so `passwd` alone enables password login. sshd stays
    off by default on the Desktop live ISO and on on the Server live ISO;
    this only decides how it accepts logins (USER 2026-11-05: if a user
    enables ssh it should accept a password)."""


class TetronosLiveLeave(Requirement):
    """tetronos-live-config ships tetronos-live-leave.service and
    /usr/libexec/tetronos/live-leave so a live session that joined a mesh
    leaves it on shutdown or reboot and no stale member is left. The unit
    is RemainAfterExit oneshot ordered after tetron.service and
    NetworkManager.service, so at shutdown its stop step runs while the
    daemon and the network are still up; TimeoutStopSec bounds it. The
    stop step does nothing when /run/tetronos/tetron-handed-over exists
    (the installer carried this membership to the target). Otherwise, for
    each network in `tetron status --json` (retried up to 5 times, 1 s
    apart, when the daemon does not answer): role Member runs
    `tetron leave <network_key>`; role Coordinator prints a warning that
    names the network and does nothing (USER 2026-11-04, join plan
    decision 18). The live hook enables the unit; the package does not."""


class PackagingManifest(Requirement):
    """packaging/manifest.toml is the single source of truth for every
    package: name, version, Debian revision, architecture, description,
    license, homepage, depends, source (release asset URL plus sha256 or a
    sha256 URL), installed files with modes, and maintainer scripts. A
    package whose upstream publishes a .deb uses kind = "deb" instead: name,
    version, revision, architecture, smoke command and the release .deb URL
    with its sha256 URL; files, scripts and control fields then come from
    that deb. Nothing is built from an unpinned or unverified input."""


class PackagingArchiveTrees(Requirement):
    """A release package whose asset is a zip archive lists [[package.trees]]
    entries: src is a directory inside the archive, dst a directory in the
    package. packaging/build.py copies every regular file under src to dst,
    mode 0755 when the archive marks it executable, else 0644. It aborts
    when the archive has an absolute path or a '..' component anywhere, a
    symlink or other non-regular file under src, or no file under src.
    src = "" is the archive root. An optional include list of globs
    (matched against the path below src) limits the copy to matching
    files. When a tree puts the upstream LICENSE into
    usr/share/doc/<name>/, the generated copyright file points to it
    instead of /usr/share/common-licenses/."""


class NerdFontSymbolsPackage(Requirement):
    """tetronos-nerd-font-symbols (kind = "release", Architecture all) is the
    symbols-only Nerd Font, the glyphs tetron-wm draws for icon_style =
    "nerd". No distribution packages it. It is built from the pinned
    NerdFontsSymbolsOnly.zip of github.com/ryanoasis/nerd-fonts, verified
    against a sha256 in the manifest (upstream publishes one SHA-256.txt
    for every asset), and installs SymbolsNerdFont-Regular.ttf and
    SymbolsNerdFontMono-Regular.ttf into
    /usr/share/fonts/truetype/nerd-font-symbols/ and the upstream MIT
    LICENSE into its doc directory. The archive's fontconfig file is left
    out: it makes Symbols Nerd Font the preferred monospace family, which
    would replace the console font; fontconfig uses the font as a fallback
    without it. Its version follows tetron core minor (0.15.0); the
    upstream version is in the source URL. kind = "release" packages are
    tetronos-built, so the release workflow attaches them with kind local
    and meta, and the tetronos apt repo serves them."""


class TetronBrowserDeb(Requirement):
    """tetron-browser is the web browser package: USER's maintained
    continuation of Carbonyl (the terminal Chromium browser, abandoned
    upstream after v0.0.3 in 2023-02), renamed as forks are. Like the other
    suite add-ons it is the release .deb of
    github.com/tetronos/tetron-browser (kind = "deb", amd64),
    verified against its published sha256 and used unchanged. Its minor
    version follows tetron core (0.15.1). The package installs
    /usr/bin/tetron-browser and the short command /usr/bin/twww (USER
    2026-11-06), wrappers that run the Chromium program
    /usr/lib/tetron-browser/tetron-browser with the profile in
    ${XDG_CONFIG_HOME:-$HOME/.config}/tetron-browser; there is no carbonyl
    command. It Conflicts with carbonyl (the earlier TetronOS package of
    upstream Carbonyl). Smoke: tetron-browser --version prints 0.15.1. It
    fixes the SIGTRAP crashes on resize found on the live Desktop ISO
    2026-11-06 (a resize run on the wrong thread from the SIGWINCH handler,
    and windows of one or two columns). The npm carbonyl (latest tag
    0.0.2-next.bacf3db, spins one core while idle) is never used."""


class PackagingRelationFields(Requirement):
    """A manifest entry may list provides, replaces and conflicts; build.py
    writes them as the Provides, Replaces and Conflicts control fields, and
    leaves a field out when its list is empty."""


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
    tetron-wm-essentials, tetron-wm-recommended, tetron-wm-extras,
    tetron-browser, tetron-appstore, tetron-stt and tetron-aimode from their published
    release debs,
    all at the same tetron minor. The four tetron-wm set packages are
    Architecture: all metapackages; packaging/tests installs them without
    Recommends. For test builds only, build.py --local-debs DIR (make
    LOCAL_DEBS=DIR) takes a deb of the same file name from DIR instead of
    the download, still checking its Package, Version and Architecture;
    a release never uses it."""


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
    tetron, tetron-tui, tetron-wm, tetronos-branding, tetronos-firstboot,
    tetronos-base-config, tetronos-apt-source, tetronos-nerd-font-symbols
    (the icon glyphs of tetron-wm and croft), network-manager, curl,
    iputils-ping, kmscon (>= 10), which brings libtsm4 (>= 4.8)
    with it, and libpam-systemd and dbus-user-session: the console login
    (agetty autologin under kmscon) gets a logind session, a systemd user
    manager and a session bus from the first boot. Without them a later
    apt install of PipeWire (tetronos-firmware) starts nothing until the
    user logs in again. curl is the invite URL fetcher of every edition (join plan
    decision 19). openssh-server is not in core:
    it comes with tetronos-server. Both come from
    trixie-backports (see KmsconFromBackports). It does not pull
    tetron-wm-desktop, so Recommends of the desktop app list never reach
    the Server image. tetron-install is added when it has a package (M5)."""


class TetronosSuiteMeta(Requirement):
    """tetronos-suite is the full suite: it Depends on tetronos-core,
    tetron-wm-recommended (which pulls tetron-wm-essentials and
    tetron-wm-desktop, each with its app list as Recommends). The GUI
    components tetron-webui and tetron-messageboard are not part of it, and
    not in the manifest. tetron-sync-receiver
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


class TetronosConsole(Requirement):
    """tetronos-console puts the kmscon console on tty1 and starts tetron-wm
    at login. It is part of every edition, live medium and installed system
    alike: tetronos-core Depends on it (with fonts-dejavu-core), and it
    Depends on kmscon (>= 10), fonts-dejavu-core and tetron-wm. It ships a
    kmsconvt@.service drop-in (10-tetronos-console.conf) that runs kmscon on
    the console with DejaVu Sans Mono 14, us keyboard, mouse on (the mouse
    tetron-wm uses comes from kmscon; a plain tty has none) and agetty with
    TERM xterm-256color; /usr/bin/tetron-session, which attaches to a running
    tetron-wm session (tetron-wm attach -d) or starts one, and falls back to a
    login shell when tetron-wm is missing or when tetron-wm ends (Quit or a
    crash: a shell on the console to edit ~/.bashrc, no login loop; exiting
    it logs out, USER 2026-11-21); /etc/profile.d/tetronos-session.sh,
    which runs tetron-session only in a login shell under kmscon or on tty1,
    never over ssh, never inside tetron-wm. Its postinst enables
    kmsconvt@tty1 and disables getty@tty1; removing the package reverts both.
    The installer keeps this package, so the first login of an installed
    system lands in the desktop (found on the P1 2026-11-20: the console and
    session script were in tetronos-live-config, which the installer purges,
    so the installed system had a plain getty and no desktop or mouse)."""


class TetronosLiveConfig(Requirement):
    """tetronos-live-config turns the live medium into a console that boots
    to tetron-wm. It is installed only in the ISO, never by tetronos-core
    or tetronos-suite. It Depends on tetronos-core, tetronos-console,
    live-boot, live-config, live-config-systemd, user-setup (live-config
    creates the live user only with it, and the image installs no
    Recommends) and sudo, and ships the kmsconvt@tty1 drop-in in
    /usr/lib/systemd/system that adds agetty autologin of the live user
    tetronos on top of the console of tetronos-console, tetronos-live-leave and
    the live ssh password units. The live user tetronos and its passwordless
    sudo come from live-config (username=tetronos on the kernel command
    line). The user is not named tetron: that name is the tetron daemon's
    system group, and adduser can not create a user whose own group already
    exists. The serial console shows a login prompt (no autologin)."""


class TetronosServerMeta(Requirement):
    """tetronos-server is the Server edition package set: it Depends on
    tetronos-core (same version), openssh-server, python3 and python3-apt.
    The Server ISO keeps sshd enabled. python3 is there because users
    expect Ansible to manage a server, and Ansible needs python3 on the
    managed node; python3-apt is what Ansible's apt module uses."""


class TetronosDesktopMeta(Requirement):
    """tetronos-desktop is the Desktop edition package set, the level above
    server (core < server < desktop < full): it Depends on tetronos-server
    (same version), tetronos-desktop-config, tetron-wm-essentials and
    tetron-wm-recommended (>= 0.15.6; they pull tetron-wm-desktop), polkitd,
    libpam-systemd and dbus-user-session (a logind session and a user bus
    for the console login), tetronos-firmware (hardware firmware, wifi
    through tetronos-server), pipewire, pipewire-alsa, pipewire-pulse, wireplumber, alsa-utils, bluez,
    brightnessctl, upower, rtkit (realtime scheduling for PipeWire),
    intel-microcode, amd64-microcode, tetron-browser (the web
    browser, >= 0.15), tetron-appstore and tetron-stt (>= 0.15.1). casttui is not part of it: a separate
    install (Settings > Cast installs it), since not every user has a Chromecast.
    Installing
    it on a server with apt (Recommends on) also brings the tools and apps
    of the three tetron-wm sets."""


class TetronosDesktopConfig(Requirement):
    """tetronos-desktop-config (kind local) ships polkit rules in
    /usr/share/polkit-1/rules.d/ that let members of netdev manage
    NetworkManager and members of users power off, reboot, suspend and
    hibernate. kmscon runs the login on a pts, so the session is not an
    active seat session and polkit's allow_active defaults do not apply.
    Bluetooth access comes from bluez's own D-Bus policy for the bluetooth
    group. On the first install its postinst also makes the machine behave
    as the Desktop ISO does (see DesktopSshOff and DesktopOpencodeInSkel):
    ssh is disabled unless running, tetron-wm-apphost.service is enabled
    for every user (systemctl --global), and opencode is installed. It
    Depends polkitd, openssh-server, tetron-wm-desktop, curl and python3."""


class DebianArchiveAreas(Requirement):
    """Every image enables the Debian archive areas main, contrib, non-free
    and non-free-firmware (live-build --archive-areas in auto/config): the
    image's /etc/apt/sources.list lists all four. non-free
    only makes packages installable (nvidia-driver and CUDA for local
    inference, unrar, intel-media-va-driver-non-free); no non-free package
    is in an image unless a manifest package Depends on it. This departs
    from Debian's default, which enables non-free-firmware but not non-free.
    A system installed before this keeps its own apt sources; nothing
    rewrites them. The image has no deb-src lines (live-build
    --apt-source-archives false in auto/config; scripts/build.sh fails the
    build if one is there): apt update fetched 100 MB of Sources indexes and
    built a 49 MB source cache, minutes on a slow USB stick (P1, 2026-11-21)."""


class TetronosFirmwareMetas(Requirement):
    """Firmware comes from two metapackages (kind meta, needs the Debian
    contrib and non-free-firmware components, which every image has in its apt sources; see DebianArchiveAreas).
    tetronos-firmware-wifi: the wifi firmware (Intel, Realtek, MediaTek,
    Atheros, Broadcom, firmware-misc-nonfree) with wpasupplicant, iw and
    wireless-regdb; tetronos-server Depends it, so every tier gets wifi and
    a laptop with only wifi can get online. tetronos-firmware: Depends
    tetronos-firmware-wifi and the rest of the hardware firmware (graphics,
    network cards, sound, USB adapters, CPU microcode) and pipewire-alsa
    and wireplumber (pipewire-alsa pulls PipeWire; wireplumber is only its Recommend, and
    the ISO installs no Recommends), so the sound card plays on a Server with firmware.
    Its postinst starts PipeWire (pipewire.socket, pipewire-pulse.socket, wireplumber.service)
    in every running user manager: apt enables those user units but does not start them,
    so a user logged in during the install would have no sound until the next boot; tetronos-desktop
    Depends it, and a Server upgrades to Server with firmware with
    apt install tetronos-firmware."""


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


class KmsconWithoutOpenGL(Requirement):
    """kmscon is built by TetronOS (manifest kind = "source", packaging/build.py in a
    debian:trixie container with packaging/kmscon/build-in-container.sh) from the
    trixie-backports source with video_drm3d and renderer_gltex disabled, as
    10.0.4-1~bpo13+1tetronos2 (tetronos1 was the OpenGL change alone), which sorts above
    the backports 10.0.4-1~bpo13+1. It
    needs no libgbm, libegl, libgles, mesa or LLVM (about 195 MB installed, 56 MB of
    the compressed server ISO). tetron-wm never uses OpenGL (kmscon only renders its
    terminal; images and video go to mpv --vo=drm), and kmscon uses its software
    renderer unless started with --hwaccel, which is off by default and which TetronOS
    never sets, so the stock kmscon was already rendering in software. The package is
    attached to the tetron-os release and so reaches the tetronos apt repository; an
    apt pin of the tetronos origin at 700 (config/common/archives/kmscon-tetronos.pref.binary)
    keeps it above the backports kmscon at 600. All tiers use it, the desktop included
    (mpv still pulls libgbm and mesa there, so only the server tiers get smaller). A
    kmscon started with --hwaccel does not use 3D acceleration; it falls back to the
    software backend. Tested: a server ISO built with it showed no slowdown (USER
    2026-11-15)."""


class KmsconTouchpadTap(Requirement):
    """The kmscon of TetronOS taps: a touchpad tap is a click (one finger left, two fingers
    right, three fingers middle), so a laptop works without pressing the pad. It is a patch
    to the kmscon source (packaging/kmscon/patches/0001-input-touchpad-tap-to-click.patch,
    branch tetron-touchpad-tap of the kmscon clone), applied by build-in-container.sh,
    with the option --touchpad-tap (off by default in the source, as libinput's default).
    The kmscon package installs scripts/etc/kmscon.conf.example as /etc/kmscon/kmscon.conf,
    and the build turns touchpad-tap on in it, so every tier taps (one kmscon, no server or
    desktop split; a user's edited kmscon.conf is kept by dpkg). A touch counts as a tap when
    it lasts less than 200 ms, moves less than 1/40 of the pad and no physical button was
    pressed. With the option on, BTN_TOOL_DOUBLETAP and BTN_TOOL_TRIPLETAP no longer send a
    middle button press. tests/test_touchpad_tap.c of the patch feeds synthetic touchpad events
    through the pointer code and checks the clicks; a hardware check on the ThinkPad P1 and
    xps-17 comes after the VM. Not sent upstream (USER 2026-11-15: PRs there are usually
    ignored, maybe later)."""


class TetronosInstallPackage(Requirement):
    """The installer ships as the local deb tetronos-install
    (/usr/sbin/tetronos-install and the static musl full screen front end
    /usr/sbin/tetronos-install-tui, built from ~/code/tetronos-install by
    make install-tui, arch amd64) until that
    repository publishes release debs. It Depends on the tools it runs
    (grub2-common, grub-pc-bin, grub-efi-amd64-bin, e2fsprogs, dosfstools,
    rsync, zstd, util-linux, fdisk (sfdisk), openssl, initramfs-tools), and tetronos-core
    Depends on it, so every edition image has the installer and an
    installed system keeps grub and fsck for kernel updates.
    The deb also ships tetronos-install-tui.service (enabled by the
    image live hook, not by the package), which runs the TUI on tty1 only when the kernel line has
    tetronos.install, so it is inert on an installed system. It has no
    Conflicts= (systemd applies that before the condition is checked and
    removed the tty1 login of every normal boot, seen on the P1 2026-11-20):
    it creates /run/tetronos-install-active while it runs, and drop-ins for
    kmsconvt@.service and getty@.service skip on that file."""
