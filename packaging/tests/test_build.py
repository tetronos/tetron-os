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


if __name__ == "__main__":
    unittest.main()
