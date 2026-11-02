#!/usr/bin/env python3
# reconcile.py -- run from the tetron-os repo root.
# Checks the automatable constraints (CON-T01..CON-T08) from spec/constraints.py.
# Requirement classes (guardrails, milestones) are verified by tests and review.
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

BUDGET_MB = 300
GUI_RE = re.compile(r"^(xserver-xorg\S*|xorg\S*|x11-common|wayland\S*|weston|lightdm|gdm3|sddm|"
                    r"task-\S*desktop|gnome-shell|plasma-desktop|xfce4\S*)$")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def tracked() -> list[str]:
    r = run(["git", "ls-files"])
    return [f for f in r.stdout.splitlines() if Path(f).is_file()]


def check_server_iso() -> dict:
    isos = sorted(glob.glob("out/tetronos-server-*.iso"))
    if not isos:
        return {"built": False, "mb": 0, "within_budget": True}
    mb = Path(isos[-1]).stat().st_size / 1e6
    return {"built": True, "iso": isos[-1], "mb": round(mb, 1), "within_budget": mb <= BUDGET_MB}


def check_no_gui() -> dict:
    allow = set()
    p = Path("config/gui-allowlist.txt")
    if p.exists():
        allow = {l.strip() for l in p.read_text().splitlines() if l.strip() and not l.startswith("#")}
    lists = sorted(glob.glob("out/*.packages"))
    if not lists:
        return {"checked": False, "violations": 0, "found": []}
    found = []
    for line in Path(lists[-1]).read_text().splitlines():
        name = line.split()[0] if line.strip() else ""
        if GUI_RE.match(name) and name not in allow:
            found.append(name)
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
        "regular": "regular)" in t,
        "firmware_per_edition": 'FW=false' in t and 'FW=true' in t and '--firmware-chroot "$FW"' in t,
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
        return {"parsed": False, "error": str(e), "unpinned": 0}
    bad = []
    for pkg in m.get("package", []):
        src = pkg.get("source", {})
        if pkg.get("kind", "release") == "meta":
            continue
        if not (pkg.get("version") and src.get("url") and (src.get("sha256") or src.get("sha256_url"))):
            bad.append(pkg.get("name", "?"))
    return {"parsed": True, "packages": len(m.get("package", [])), "unpinned": len(bad), "names": bad}


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
    }
    print(json.dumps(ctx, indent=2))
    ok = (
        ctx["server_iso"]["within_budget"]
        and ctx["no_gui"]["violations"] == 0
        and ctx["secrets"]["count"] == 0
        and ctx["scripts"]["failures"] == 0
        and ctx["editions"]["server"] and ctx["editions"]["regular"] and ctx["editions"]["firmware_per_edition"]
        and ctx["legacy_name"]["count"] == 0
        and ctx["local_docs"]["ignored"] and ctx["local_docs"]["tracked"] == 0
        and ctx["manifest"]["parsed"] and ctx["manifest"]["unpinned"] == 0
    )
    sys.exit(0 if ok else 1)
