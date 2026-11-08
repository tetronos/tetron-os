#!/usr/bin/env python3
"""Build the TetronOS .debs from packaging/manifest.toml. Stdlib + dpkg-deb only.

Usage: build.py [--only NAME] [--out DIR] [--list-tests]
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
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


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"  download {url}")
    try:
        with urllib.request.urlopen(url, timeout=60) as r, tmp.open("wb") as f:
            shutil.copyfileobj(r, f)
    except OSError as e:
        die(f"cannot download {url}: {e}")
    tmp.replace(dest)


def expected_sha(src: dict) -> str:
    if src.get("sha256"):
        return src["sha256"].lower()
    try:
        with urllib.request.urlopen(src["sha256_url"], timeout=30) as r:
            return r.read().decode().split()[0].lower()
    except (OSError, IndexError) as e:
        die(f"cannot read checksum {src['sha256_url']}: {e}")


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


def take_release_deb(pkg: dict, out: Path) -> Path:
    """kind = "deb": verify the published deb and copy it unchanged."""
    name = pkg["name"]
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="build only this package")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--list-tests", action="store_true", help="print 'name|smoke command' lines")
    a = ap.parse_args()
    top = tomllib.loads((HERE / "manifest.toml").read_text())
    pkgs = [p for p in top["package"] if not a.only or p["name"] == a.only]
    if not pkgs:
        die(f"no such package: {a.only}")
    if a.list_tests:
        for p in pkgs:
            print(f"{p['name']}|{p['version']}-{p['revision']}|{p.get('smoke', '')}")
        return
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", top["source_date_epoch"]))
    for p in pkgs:
        if p.get("kind") == "deb":
            take_release_deb(p, Path(a.out))
        else:
            build_one(p, top, Path(a.out), epoch)


if __name__ == "__main__":
    main()
