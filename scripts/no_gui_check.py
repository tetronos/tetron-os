#!/usr/bin/env python3
"""Report GUI session packages in an image package list.

Usage: no_gui_check.py PACKAGES_FILE [ALLOWLIST]
PACKAGES_FILE has one package per line, name first (filesystem.packages).
Prints each violation and exits 1 if there is any.
"""
import re
import sys
from pathlib import Path

GUI_RE = re.compile(r"^(xserver-xorg\S*|xorg\S*|x11-common|wayland\S*|weston|lightdm|gdm3|sddm|"
                    r"task-\S*desktop|gnome-shell|plasma-desktop|xfce4\S*)$")


def allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {l.strip() for l in path.read_text().splitlines() if l.strip() and not l.startswith("#")}


def violations(packages: Path, allow: set[str]) -> list[str]:
    names = (l.split()[0].split(":")[0] for l in packages.read_text().splitlines() if l.strip())
    return [n for n in names if GUI_RE.match(n) and n not in allow]


def main() -> None:
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__.strip())
    allow = allowlist(Path(sys.argv[2] if len(sys.argv) == 3 else "config/gui-allowlist.txt"))
    bad = violations(Path(sys.argv[1]), allow)
    for n in bad:
        print(f"no-gui: forbidden package {n}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
