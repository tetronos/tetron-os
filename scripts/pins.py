#!/usr/bin/env python3
"""Compare the release debs pinned in packaging/manifest.toml with the latest
release tags of their repositories, and optionally move the pins.

  scripts/pins.py check     print pinned and latest per repository, exit 1 on a difference
  scripts/pins.py update    rewrite packaging/manifest.toml to the latest tags (then review git diff)

Tags are read with git ls-remote (public repos, no login): vMAJOR.MINOR.PATCH,
tags with a - suffix (pre-releases) are skipped. Only kind = "deb" packages whose
url is a github.com release download are looked at. A package that is new in a
release must be added to the manifest by hand.
"""
import re
import subprocess
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent.parent / "packaging" / "manifest.toml"
URL = re.compile(r"https://github\.com/([^/]+)/([^/]+)/releases/download/v([0-9][0-9.]*)/")


def latest(org: str, repo: str) -> str:
    out = subprocess.run(["git", "ls-remote", "--tags", "--refs", f"https://github.com/{org}/{repo}", "v[0-9]*"],
                         capture_output=True, text=True).stdout
    tags = [l.split("refs/tags/v")[1] for l in out.splitlines() if "refs/tags/v" in l]
    tags = [t for t in tags if re.fullmatch(r"[0-9]+(\.[0-9]+)*", t)]
    tags.sort(key=lambda t: [int(x) for x in t.split(".")])
    return tags[-1] if tags else ""


def blocks(text: str) -> list[str]:
    parts = re.split(r"(?m)^(?=\[\[package\]\]$)", text)
    return parts


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode not in ("check", "update"):
        print(__doc__)
        return 2
    text = MANIFEST.read_text()
    cache: dict = {}
    pinned: dict = {}
    out = []
    for b in blocks(text):
        m = URL.search(b)
        if m and 'kind = "deb"' in b:
            org, repo, old = m.groups()
            if (org, repo) not in cache:
                cache[(org, repo)] = latest(org, repo)
            new = cache[(org, repo)]
            pinned.setdefault(repo, set()).add(old)
            if mode == "update" and new and new != old:
                b = b.replace(f"/v{old}/", f"/v{new}/").replace(f"_{old}-", f"_{new}-")
                b = re.sub(r'(?m)^version = "%s"$' % re.escape(old), f'version = "{new}"', b)
        out.append(b)
    bad = 0
    for (org, repo), new in cache.items():
        old = ", ".join(sorted(pinned[repo]))
        mark = "ok  " if old == new else "DIFF"
        bad += old != new
        print(f"{mark} {repo}: pinned {old} latest {new or 'none found'}")
    if mode == "update":
        MANIFEST.write_text("".join(out))
        print("manifest updated" if bad else "nothing to change")
        return 0
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
