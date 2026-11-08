#!/usr/bin/env python3
"""Build the TetronOS .debs from packaging/manifest.toml. Stdlib + dpkg-deb only.

Usage: build.py [--only NAME] [--out DIR] [--list-tests] [--list-debs]
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def die(msg: str) -> None:
    print(f"build.py: error: {msg}", file=sys.stderr)
    sys.exit(1)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def retried(what: str, url: str, read, tries: int = 5, wait: float = 10.0):
    """read(url) with retries: release downloads answer 502/503/504 at times."""
    for i in range(tries):
        try:
            return read(url)
        except OSError as e:
            if i == tries - 1:
                die(f"cannot {what} {url}: {e}")
            print(f"  retry {i + 1}/{tries - 1} in {wait * (i + 1):.0f}s: {e}")
            time.sleep(wait * (i + 1))


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"  download {url}")

    def read(u):
        with urllib.request.urlopen(u, timeout=60) as r, tmp.open("wb") as f:
            shutil.copyfileobj(r, f)
    retried("download", url, read)
    tmp.replace(dest)


def expected_sha(src: dict) -> str:
    if src.get("sha256"):
        return src["sha256"].lower()
    def read(u):
        with urllib.request.urlopen(u, timeout=30) as r:
            return r.read().decode()
    words = retried("read checksum", src["sha256_url"], read).split()
    if not words:
        die(f"empty checksum file {src['sha256_url']}")
    return words[0].lower()


def get_asset(pkg: dict) -> Path:
    src = pkg["source"]
    name = pkg["name"]
    dest = HERE / "cache" / f"{name}-{pkg['version']}-{Path(src['url']).name}"
    want = expected_sha(src)
    if dest.exists() and sha256_of(dest) != want:
        print(f"  cached {dest.name} fails checksum, re-downloading")
        dest.unlink()
    if not dest.exists():
        fetch(src["url"], dest)
    got = sha256_of(dest)
    if got != want:
        dest.unlink()
        die(f"{name}: sha256 mismatch for {src['url']}: expected {want}, got {got}")
    return dest


def control(pkg: dict, maintainer: str, size_kib: int) -> str:
    desc = pkg["description"]
    longd = "\n".join(" " + (l if l.strip() else ".") for l in pkg.get("long_description", "").strip().splitlines())
    fields = [
        ("Package", pkg["name"]),
        ("Version", f"{pkg['version']}-{pkg['revision']}"),
        ("Architecture", pkg["arch"]),
        ("Maintainer", maintainer),
        ("Installed-Size", str(size_kib)),
        ("Depends", ", ".join(pkg.get("depends", []))),
        ("Recommends", ", ".join(pkg.get("recommends", []))),
        ("Provides", ", ".join(pkg.get("provides", []))),
        ("Breaks", ", ".join(pkg.get("breaks", []))),
        ("Replaces", ", ".join(pkg.get("replaces", []))),
        ("Conflicts", ", ".join(pkg.get("conflicts", []))),
        ("Section", pkg.get("section", "misc")),
        ("Priority", pkg.get("priority", "optional")),
        ("Homepage", pkg.get("homepage", "")),
    ]
    out = "".join(f"{k}: {v}\n" for k, v in fields if v)
    return out + f"Description: {desc}\n" + (longd + "\n" if longd else "")


def copyright_text(pkg: dict, upstream_license: bool = False) -> str:
    if pkg.get("kind") == "meta":
        return ("This is a metapackage of TetronOS. It has no content of its own:\n"
                "it only depends on other packages, each with its own copyright file.\n")
    if pkg.get("kind") == "local":
        return ("This package is TetronOS configuration. Its files are maintained in\n"
                "the TetronOS repository; it contains no third-party code.\n")
    where = (f"/usr/share/doc/{pkg['name']}/LICENSE" if upstream_license
             else f"/usr/share/common-licenses/{pkg['license']}")
    return (f"Upstream: {pkg.get('homepage', '')}\n"
            f"License: {pkg['license']}\n"
            f"The full license text is in {where}.\n")


def deb_filename(pkg: dict) -> str:
    return f"{pkg['name']}_{pkg['version']}-{pkg['revision']}_{pkg['arch']}.deb"


def deb_field_mismatches(fields: dict, pkg: dict) -> list[str]:
    want = {"Package": pkg["name"], "Version": f"{pkg['version']}-{pkg['revision']}",
            "Architecture": pkg["arch"]}
    return [f"{k}: expected {v}, deb has {fields.get(k, '(missing)')}"
            for k, v in want.items() if fields.get(k) != v]


def deb_fields(path: Path) -> dict:
    r = subprocess.run(["dpkg-deb", "-f", str(path), "Package", "Version", "Architecture"],
                       capture_output=True, text=True)
    if r.returncode:
        die(f"cannot read control fields of {path}: {r.stderr.strip()}")
    return dict(line.split(": ", 1) for line in r.stdout.splitlines() if ": " in line)


def take_release_deb(pkg: dict, out: Path, local: Path | None = None) -> Path:
    """kind = "deb": verify the published deb and copy it unchanged. With
    local (--local-debs, test builds only), a deb of the same file name in
    that directory is taken instead of the download and its checksum."""
    name = pkg["name"]
    mine = local / deb_filename(pkg) if local else None
    if mine and mine.is_file():
        print(f"{name} {pkg['version']}-{pkg['revision']} (LOCAL deb {mine}, not the release)")
        asset = mine
    else:
        print(f"{name} {pkg['version']}-{pkg['revision']} (release deb)")
        asset = get_asset(pkg)
    bad = deb_field_mismatches(deb_fields(asset), pkg)
    if bad:
        die(f"{name}: release deb does not match the manifest: " + "; ".join(bad))
    out.mkdir(parents=True, exist_ok=True)
    target = out / deb_filename(pkg)
    shutil.copyfile(asset, target)
    print(f"  -> {target} ({target.stat().st_size // 1024} KiB)")
    return target


def extract_trees(pkg: dict, archive: Path, stage: Path) -> None:
    """Copy each [[package.trees]] src directory of a zip asset to its dst:
    regular files only, 0755 if executable in the archive, else 0644.
    src "" is the archive root; include (globs on the path below src) limits
    the copy to matching files."""
    from fnmatch import fnmatchcase
    import stat
    with zipfile.ZipFile(archive) as z:
        for t in pkg.get("trees", []):
            prefix = t["src"].strip("/") + "/" if t["src"].strip("/") else ""
            include = t.get("include", [])
            n = 0
            for zi in z.infolist():
                name = zi.filename
                parts = Path(name).parts
                if name.startswith("/") or ".." in parts:
                    die(f"{pkg['name']}: unsafe path in archive: {name}")
                if not name.startswith(prefix) or zi.is_dir():
                    continue
                if include and not any(fnmatchcase(name[len(prefix):], g) for g in include):
                    continue
                mode = zi.external_attr >> 16
                if stat.S_ISLNK(mode) or (mode and not stat.S_ISREG(mode)):
                    die(f"{pkg['name']}: not a regular file in archive: {name}")
                dst = stage / t["dst"] / name[len(prefix):]
                dst.parent.mkdir(parents=True, exist_ok=True)
                with z.open(zi) as src, dst.open("wb") as f:
                    shutil.copyfileobj(src, f)
                dst.chmod(0o755 if mode & 0o111 else 0o644)
                n += 1
            if not n:
                die(f"{pkg['name']}: no files under {prefix or 'the root'} in {archive.name}")


def build_one(pkg: dict, top: dict, out: Path, epoch: int) -> Path:
    name = pkg["name"]
    print(f"{name} {pkg['version']}-{pkg['revision']}")
    asset = None if pkg.get("kind") in ("meta", "local") else get_asset(pkg)
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "stage"
        for f in pkg.get("files", []):
            src = asset if f["src"] == "asset" else HERE / f["src"]
            if not src.exists():
                die(f"{name}: missing file {src}")
            dst = stage / f["dst"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            dst.chmod(int(f["mode"], 8))
        if pkg.get("trees"):
            extract_trees(pkg, asset, stage)
        doc = stage / "usr/share/doc" / name / "copyright"
        if not doc.exists():  # a package may ship the upstream license text
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text(copyright_text(pkg, (doc.parent / "LICENSE").exists()))
            doc.chmod(0o644)
        files = sorted(p for p in stage.rglob("*") if p.is_file())
        size_kib = (sum(p.stat().st_size for p in files) + 1023) // 1024
        deb = stage / "DEBIAN"
        deb.mkdir()
        (deb / "control").write_text(control(pkg, top["maintainer"], size_kib))
        (deb / "md5sums").write_text("".join(
            f"{hashlib.md5(p.read_bytes()).hexdigest()}  {p.relative_to(stage)}\n" for p in files))
        conf = [f"/{p.relative_to(stage)}\n" for p in files if p.relative_to(stage).parts[0] == "etc"]
        if conf:
            (deb / "conffiles").write_text("".join(conf))
        for script, path in pkg.get("scripts", {}).items():
            dst = deb / script
            shutil.copyfile(HERE / path, dst)
            dst.chmod(0o755)
        for p in [stage, *stage.rglob("*")]:
            os.utime(p, (epoch, epoch), follow_symlinks=False)
            if p.is_dir():
                p.chmod(0o755)
        out.mkdir(parents=True, exist_ok=True)
        target = out / deb_filename(pkg)
        env = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
        r = subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(stage), str(target)],
                           env=env, capture_output=True, text=True)
        if r.returncode:
            die(f"{name}: dpkg-deb failed:\n{r.stderr}")
    print(f"  -> {target} ({target.stat().st_size // 1024} KiB)")
    return target


OWN_KINDS = ("local", "meta", "release")
DEP_RE = re.compile(r"^\s*([a-z0-9][a-z0-9+.-]*)\s*(?:\(\s*(<<|<=|=|>=|>>)\s*([^)\s]+)\s*\))?\s*$")


def version_key(v: str) -> tuple:
    """0.15.0-6 -> (0, 15, 0, 6); our own versions are numeric only."""
    return tuple(int(x) for x in re.split(r"[.-]", v))


def next_minor(version: str) -> str:
    major, minor = version.split(".")[:2]
    return f"{major}.{int(minor) + 1}"


def pin_problems(packages: list[dict]) -> list[str]:
    """Relations to packages built here must be a floor plus the next core
    minor as ceiling: `name (>= FLOOR), name (<< NEXT_MINOR)`, never `=`,
    and FLOOR no higher than the version the manifest builds."""
    own = {p["name"]: p for p in packages if p.get("kind") in OWN_KINDS}
    bad = []
    for p in packages:
        rels = {}
        for field in ("depends", "recommends", "breaks", "replaces", "conflicts"):
            for entry in p.get(field, []):
                for alt in entry.split("|"):
                    m = DEP_RE.match(alt)
                    if not m:
                        bad.append(f"{p['name']}: can not parse {field} entry {alt!r}")
                        continue
                    name, op, ver = m.groups()
                    if name in own and field in ("depends", "recommends"):
                        rels.setdefault(name, []).append((op, ver))
        for name, ops in rels.items():
            dep = own[name]
            have = f"{dep['version']}-{dep['revision']}"
            floors = [v for o, v in ops if o == ">="]
            ceils = [v for o, v in ops if o == "<<"]
            other = [f"{o} {v}" for o, v in ops if o not in (">=", "<<")]
            if other or len(floors) != 1 or len(ceils) != 1:
                bad.append(f"{p['name']} -> {name}: write \"{name} (>= FLOOR)\", \"{name} (<< {next_minor(dep['version'])})\" "
                           f"(found {', '.join(f'{o} {v}' if o else 'no version' for o, v in ops)})")
                continue
            if version_key(floors[0]) > version_key(have):
                bad.append(f"{p['name']} -> {name}: floor {floors[0]} is above the built {have} (uninstallable)")
            if ceils[0] != next_minor(dep["version"]):
                bad.append(f"{p['name']} -> {name}: ceiling << {ceils[0]}, expected << {next_minor(dep['version'])}")
    return bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="build only this package")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--list-tests", action="store_true", help="print 'name|smoke command' lines")
    ap.add_argument("--list-debs", action="store_true", help="print the .deb file names this manifest makes")
    ap.add_argument("--local-debs", metavar="DIR",
                    help="test builds only: take a kind = deb package from DIR when DIR has its file name")
    a = ap.parse_args()
    top = tomllib.loads((HERE / "manifest.toml").read_text())
    problems = pin_problems(top["package"])
    if problems:
        die("package relations (rules in the packaging/manifest.toml header):\n  " + "\n  ".join(problems))
    pkgs = [p for p in top["package"] if not a.only or p["name"] == a.only]
    if not pkgs:
        die(f"no such package: {a.only}")
    if a.list_debs:
        for p in pkgs:
            print(deb_filename(p))
        return
    if a.list_tests:
        for p in pkgs:
            print(f"{p['name']}|{p['version']}-{p['revision']}|{p.get('smoke', '')}")
        return
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", top["source_date_epoch"]))
    for p in pkgs:
        if p.get("kind") == "deb":
            take_release_deb(p, Path(a.out), Path(a.local_debs) if a.local_debs else None)
        else:
            build_one(p, top, Path(a.out), epoch)


if __name__ == "__main__":
    main()
