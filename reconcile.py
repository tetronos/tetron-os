#!/usr/bin/env python3
# reconcile.py -- run from the tetron-os repo root.
# Checks the automatable constraints (CON-T01..CON-T10) from spec/constraints.py.
# Requirement classes (guardrails, milestones) are verified by tests and review.
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
import no_gui_check  # noqa: E402

TARGET_MB = 300  # a target, not a gate: over it is fine when SIZES.md records the size


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def tracked() -> list[str]:
    r = run(["git", "ls-files"])
    return [f for f in r.stdout.splitlines() if Path(f).is_file()]


def check_server_iso() -> dict:
    isos = sorted(i for i in glob.glob("out/tetronos-server-*.iso") if "-fw-" not in i)
    if not isos:
        return {"built": False, "mb": 0, "target_mb": TARGET_MB, "over_target": False, "recorded": True}
    mb = Path(isos[-1]).stat().st_size / 1e6
    sizes = Path("SIZES.md").read_text() if Path("SIZES.md").exists() else ""
    return {"built": True, "iso": isos[-1], "mb": round(mb, 1), "target_mb": TARGET_MB,
            "over_target": mb > TARGET_MB, "recorded": f"{round(mb)} MB" in sizes}


def check_no_gui() -> dict:
    lists = sorted(glob.glob("out/*.packages"))
    if not lists:
        return {"checked": False, "violations": 0, "found": []}
    found = no_gui_check.violations(Path(lists[-1]), no_gui_check.allowlist(Path("config/gui-allowlist.txt")))
    return {"checked": True, "list": lists[-1], "violations": len(found), "found": found}


def check_secrets() -> dict:
    pat = re.compile(r"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY|tetron://[A-Za-z0-9+/=_-]{20,}|ghp_[A-Za-z0-9]{20,}")
    hits = []
    for f in tracked():
        try:
            if pat.search(Path(f).read_text(errors="ignore")):
                hits.append(f)
        except OSError:
            pass
    return {"count": len(hits), "files": hits}


def check_scripts() -> dict:
    bad = []
    for pattern in ("scripts/*.sh", "scripts/vm.sh", "auto/*", "packaging/*.sh", "packaging/**/*.sh"):
        for f in glob.glob(pattern, recursive=True):
            if Path(f).is_file() and run(["sh", "-n", f]).returncode != 0:
                bad.append(f)
    return {"failures": len(bad), "files": sorted(set(bad))}


def check_editions() -> dict:
    t = Path("auto/config").read_text() if Path("auto/config").exists() else ""
    return {
        "server": "server)" in t,
        "desktop": "desktop)" in t,
        "firmware_axis": "FIRMWARE" in t and 'FW=false' in t and 'FW=true' in t and '--firmware-chroot "$FW"' in t,
    }


def check_legacy_name() -> dict:
    hits = []
    for f in tracked():
        # The spec and its libspec snapshot store name the retired word on purpose (CON-T06).
        if f == "reconcile.py" or f.startswith("spec/") or f.startswith(".libspec/"):
            continue
        try:
            if re.search(r"tuiui", Path(f).read_text(errors="ignore"), re.I):
                hits.append(f)
        except OSError:
            pass
    return {"count": len(hits), "files": hits}


def check_manifest() -> dict:
    import tomllib
    p = Path("packaging/manifest.toml")
    if not p.exists():
        return {"parsed": True, "packages": 0, "unpinned": 0}
    try:
        m = tomllib.loads(p.read_text())
    except tomllib.TOMLDecodeError as e:
        return {"parsed": False, "error": str(e), "unpinned": 0, "bad_relations": 0}
    bad = []
    for pkg in m.get("package", []):
        src = pkg.get("source", {})
        if pkg.get("kind", "release") in ("meta", "local"):
            continue
        if not (pkg.get("version") and src.get("url") and (src.get("sha256") or src.get("sha256_url"))):
            bad.append(pkg.get("name", "?"))
    sys.path.insert(0, str(Path("packaging").resolve()))
    import build
    rel = build.pin_problems(m.get("package", []))
    return {"parsed": True, "packages": len(m.get("package", [])), "unpinned": len(bad), "names": bad,
            "bad_relations": len(rel), "relations": rel}


def parity_rows(deb: Path) -> list | None:
    """The rows of the parity table in a tetron-wm deb, or None when it has none."""
    import io
    import tarfile
    import tomllib
    r = subprocess.run(["dpkg-deb", "--fsys-tarfile", str(deb)], capture_output=True)
    if r.returncode != 0:
        return None
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as t:
        try:
            f = t.extractfile("./usr/share/doc/tetron-wm/parity.toml")
        except KeyError:
            return None
        return tomllib.loads(f.read().decode()).get("row", []) if f else None


def check_parity() -> dict:
    """CON-T10: the Desktop ISO carries what tetron-wm's parity table expects."""
    debs = [l for l in run([sys.executable, "packaging/build.py", "--list-debs"]).stdout.split() if l.startswith("tetron-wm_")]
    lists = sorted(glob.glob("out/tetronos-desktop-*.packages"))
    deb = Path("packaging/out") / debs[0] if debs else None
    if not deb or not deb.exists() or not lists:
        return {"checked": False, "ok": True, "why": "no tetron-wm deb built or no Desktop package list"}
    rows = parity_rows(deb)
    version = deb.name.split("_")[1]
    if rows is None:
        # tetron-wm ships the table from 0.15.6 on.
        old = tuple(int(x) for x in version.split("-")[0].split(".")) < (0, 15, 6)
        return {"checked": False, "ok": old, "why": f"{deb.name} has no parity table"}
    have = {l.split("\t")[0] for l in Path(lists[-1]).read_text().splitlines() if l}
    hooks = "".join(Path(h).read_text() for h in sorted(glob.glob("config/*/hooks/live/*")) if "server" not in h)
    problems = []
    for r in rows:
        problems += [f"step {r['step']} ({r['what']}): package {p} not in {lists[-1]}" for p in r.get("iso_packages", []) if p not in have]
        for u in r.get("iso_units", []):
            stem = u.replace("@.service", "@").replace(".service", "")
            if stem not in hooks:
                problems.append(f"step {r['step']} ({r['what']}): unit {u} is not enabled by a Desktop hook")
    return {"checked": True, "ok": not problems, "deb": deb.name, "list": lists[-1], "rows": len(rows), "problems": problems}


def check_local_docs() -> dict:
    ignored = run(["git", "check-ignore", "-q", "DO-NOT-COMMIT/x"]).returncode == 0
    tracked_n = len([f for f in run(["git", "ls-files", "DO-NOT-COMMIT"]).stdout.splitlines() if f])
    return {"ignored": ignored, "tracked": tracked_n}


if __name__ == "__main__":
    ctx = {
        "server_iso": check_server_iso(),
        "no_gui": check_no_gui(),
        "secrets": check_secrets(),
        "scripts": check_scripts(),
        "editions": check_editions(),
        "legacy_name": check_legacy_name(),
        "local_docs": check_local_docs(),
        "manifest": check_manifest(),
        "parity": check_parity(),
    }
    print(json.dumps(ctx, indent=2))
    ok = (
        (not ctx["server_iso"]["over_target"] or ctx["server_iso"]["recorded"])
        and ctx["no_gui"]["violations"] == 0
        and ctx["secrets"]["count"] == 0
        and ctx["scripts"]["failures"] == 0
        and ctx["editions"]["server"] and ctx["editions"]["desktop"] and ctx["editions"]["firmware_axis"]
        and ctx["legacy_name"]["count"] == 0
        and ctx["local_docs"]["ignored"] and ctx["local_docs"]["tracked"] == 0
        and ctx["manifest"]["parsed"] and ctx["manifest"]["unpinned"] == 0
        and ctx["manifest"].get("bad_relations", 0) == 0
        and ctx["parity"]["ok"]
    )
    sys.exit(0 if ok else 1)
