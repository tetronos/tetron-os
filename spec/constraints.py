from libspec import Constraint

# Enforced by reconcile.py (run: python3 reconcile.py). enforcement_logic reads
# the JSON context that reconcile.py prints.


class ServerIsoUnderBudget(Constraint):
    """CONSTRAINT-ID: CON-T01

    The newest out/tetronos-server-*.iso is at most the 300 MB target, or
    its size is recorded in SIZES.md. The target is not a gate.
    ENFORCEMENT (reconcile.py): server_iso.over_target is false or
    server_iso.recorded is true. Passes when no ISO has been built yet.
    """
    constraint_id = "CON-T01"
    enforcement_logic = "{{ not server_iso.over_target or server_iso.recorded }}"


class NoGuiPackages(Constraint):
    """CONSTRAINT-ID: CON-T02

    The built image package list (out/*.packages) contains no X11, Wayland,
    display manager or desktop environment packages (config/gui-allowlist.txt
    entries excepted).
    ENFORCEMENT (reconcile.py): no_gui.violations equals 0.
    """
    constraint_id = "CON-T02"
    enforcement_logic = "{{ no_gui.violations == 0 }}"


class NoSecretsInTree(Constraint):
    """CONSTRAINT-ID: CON-T03

    No private keys, invite tickets or tokens in tracked files.
    ENFORCEMENT (reconcile.py): secrets.count equals 0.
    """
    constraint_id = "CON-T03"
    enforcement_logic = "{{ secrets.count == 0 }}"


class ScriptsParse(Constraint):
    """CONSTRAINT-ID: CON-T04

    Every shell script under scripts/, auto/ and packaging/ parses (sh -n).
    ENFORCEMENT (reconcile.py): scripts.failures equals 0.
    """
    constraint_id = "CON-T04"
    enforcement_logic = "{{ scripts.failures == 0 }}"


class EditionsSelectable(Constraint):
    """CONSTRAINT-ID: CON-T05

    auto/config handles both the server and regular editions, with
    --firmware-chroot decided per edition.
    ENFORCEMENT (reconcile.py): editions.server and editions.regular are true.
    """
    constraint_id = "CON-T05"
    enforcement_logic = "{{ editions.server and editions.regular and editions.firmware_per_edition }}"


class NoLegacyWmName(Constraint):
    """CONSTRAINT-ID: CON-T06

    The retired window manager name (tuiui) does not appear in tracked files.
    ENFORCEMENT (reconcile.py): legacy_name.count equals 0.
    """
    constraint_id = "CON-T06"
    enforcement_logic = "{{ legacy_name.count == 0 }}"


class LocalDocsIgnored(Constraint):
    """CONSTRAINT-ID: CON-T07

    DO-NOT-COMMIT/ is gitignored and nothing under it is tracked.
    ENFORCEMENT (reconcile.py): local_docs.ignored is true and
    local_docs.tracked equals 0.
    """
    constraint_id = "CON-T07"
    enforcement_logic = "{{ local_docs.ignored and local_docs.tracked == 0 }}"


class ManifestPinned(Constraint):
    """CONSTRAINT-ID: CON-T08

    Every package in packaging/manifest.toml has a version, a release source
    URL and a sha256 (inline or by URL).
    ENFORCEMENT (reconcile.py): manifest.unpinned equals 0 and manifest.parsed
    is true.
    """
    constraint_id = "CON-T08"
    enforcement_logic = "{{ manifest.parsed and manifest.unpinned == 0 }}"
