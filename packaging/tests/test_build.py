#!/usr/bin/env python3
"""Unit tests for packaging/build.py. Run: python3 packaging/tests/test_build.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build  # noqa: E402

PKG = {"name": "tetron", "version": "0.15.0", "revision": "1", "arch": "amd64"}
GOOD = {"Package": "tetron", "Version": "0.15.0-1", "Architecture": "amd64"}


class DebFieldMismatches(unittest.TestCase):
    def test_matching_fields(self):
        self.assertEqual(build.deb_field_mismatches(GOOD, PKG), [])

    def test_each_field_mismatch_is_reported(self):
        for field, bad in (("Package", "tetron-tui"), ("Version", "0.14.3-1"), ("Architecture", "arm64")):
            got = build.deb_field_mismatches(dict(GOOD, **{field: bad}), PKG)
            self.assertEqual(len(got), 1, field)
            self.assertIn(field, got[0])

    def test_missing_field_is_reported(self):
        got = build.deb_field_mismatches({"Package": "tetron", "Version": "0.15.0-1"}, PKG)
        self.assertEqual(len(got), 1)
        self.assertIn("Architecture", got[0])


class DebTarget(unittest.TestCase):
    def test_canonical_name(self):
        self.assertEqual(build.deb_filename(PKG), "tetron_0.15.0-1_amd64.deb")


META = {"name": "tetronos-core", "kind": "meta", "version": "0.15.0", "revision": "1", "arch": "all",
        "description": "TetronOS core", "depends": ["tetron (>= 0.15)", "openssh-server"],
        "recommends": ["htop"]}
TOP = {"maintainer": "TetronOS <noreply@tetron.invalid>"}


class MetaControl(unittest.TestCase):
    def test_depends_and_recommends(self):
        c = build.control(META, TOP["maintainer"], 1)
        self.assertIn("Depends: tetron (>= 0.15), openssh-server\n", c)
        self.assertIn("Recommends: htop\n", c)
        self.assertIn("Architecture: all\n", c)

    def test_meta_copyright_says_no_content(self):
        self.assertIn("no content of its own", build.copyright_text(META))


class MetaBuild(unittest.TestCase):
    def test_builds_without_download_and_only_ships_copyright(self):
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as td:
            deb = build.build_one(META, TOP, Path(td), 1792998000)
            self.assertEqual(deb.name, "tetronos-core_0.15.0-1_all.deb")
            files = [l.split()[-1] for l in subprocess.run(["dpkg-deb", "-c", str(deb)], capture_output=True,
                     text=True, check=True).stdout.splitlines() if not l.endswith("/")]
            self.assertEqual(files, ["./usr/share/doc/tetronos-core/copyright"])
            self.assertEqual(build.deb_fields(deb)["Architecture"], "all")

    def test_reproducible(self):
        import tempfile
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            da = build.build_one(META, TOP, Path(a), 1792998000).read_bytes()
            db = build.build_one(META, TOP, Path(b), 1792998000).read_bytes()
            self.assertEqual(da, db)


if __name__ == "__main__":
    unittest.main()
