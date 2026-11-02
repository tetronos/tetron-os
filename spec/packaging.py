from libspec import Requirement


class TetronDeb(Requirement):
    """The tetron core daemon and CLI are packaged as a .deb named tetron,
    built by packaging/ from the pinned upstream release asset (static musl
    x86_64), checksum verified before packaging. Installs /usr/bin/tetron.
    The package version equals the upstream version with a Debian revision
    (for example 0.14.3-1)."""


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
    sha256 URL), installed files with modes, and maintainer scripts. Nothing
    is built from an unpinned or unverified input."""


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
