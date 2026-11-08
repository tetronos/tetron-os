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

    def test_relation_fields(self):
        pkg = dict(META, provides=["carbonyl"], replaces=["carbonyl"], conflicts=["carbonyl"])
        c = build.control(pkg, TOP["maintainer"], 1)
        for f in ("Provides", "Replaces", "Conflicts"):
            self.assertIn(f"{f}: carbonyl\n", c)
        self.assertNotIn("Provides:", build.control(META, TOP["maintainer"], 1))

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


LOCAL = {"name": "tetronos-live-config", "kind": "local", "version": "0.15.0", "revision": "1",
         "arch": "all", "description": "TetronOS live", "depends": ["tetronos-core (>= 0.15.0-1)", "tetronos-core (<< 0.16)"],
         "files": [{"src": "files/tetronos-live-config/tetron-session", "dst": "usr/bin/tetron-session", "mode": "0755"},
                   {"src": "files/tetronos-live-config/tetronos-session.sh",
                    "dst": "etc/profile.d/tetronos-session.sh", "mode": "0644"}],
         "scripts": {"postinst": "files/tetronos-live-config/postinst"}}


class LocalBuild(unittest.TestCase):
    def test_builds_from_repo_files_without_download(self):
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as td:
            deb = build.build_one(LOCAL, TOP, Path(td), 1792998000)
            listing = subprocess.run(["dpkg-deb", "-c", str(deb)], capture_output=True, text=True,
                                     check=True).stdout.splitlines()
            files = {l.split()[-1]: l.split()[0] for l in listing if not l.endswith("/")}
            self.assertEqual(files["./usr/bin/tetron-session"], "-rwxr-xr-x")
            self.assertEqual(files["./etc/profile.d/tetronos-session.sh"], "-rw-r--r--")
            conf = subprocess.run(["dpkg-deb", "-I", str(deb), "conffiles"], capture_output=True, text=True,
                                  check=True).stdout
            self.assertEqual(conf, "/etc/profile.d/tetronos-session.sh\n")

    def test_local_copyright_says_tetronos_configuration(self):
        self.assertIn("TetronOS configuration", build.copyright_text(LOCAL))


def own(name, rev="1", **kw):
    return dict({"name": name, "kind": "meta", "version": "0.15.0", "revision": rev}, **kw)


class PinProblems(unittest.TestCase):
    def test_floor_and_minor_ceiling_pass(self):
        pk = [own("a", "3"), own("b", depends=["a (>= 0.15.0-2)", "a (<< 0.16)", "curl"])]
        self.assertEqual(build.pin_problems(pk), [])

    def test_exact_pin_refused(self):
        got = build.pin_problems([own("a"), own("b", depends=["a (= 0.15.0-1)"])])
        self.assertEqual(len(got), 1)
        self.assertIn("b -> a", got[0])

    def test_missing_ceiling_or_version_refused(self):
        self.assertEqual(len(build.pin_problems([own("a"), own("b", depends=["a (>= 0.15.0-1)"])])), 1)
        self.assertEqual(len(build.pin_problems([own("a"), own("b", depends=["a"])])), 1)

    def test_floor_above_built_revision_refused(self):
        got = build.pin_problems([own("a", "2"), own("b", depends=["a (>= 0.15.0-3)", "a (<< 0.16)"])])
        self.assertIn("uninstallable", got[0])

    def test_wrong_ceiling_refused(self):
        got = build.pin_problems([own("a"), own("b", depends=["a (>= 0.15.0-1)", "a (<< 0.17)"])])
        self.assertIn("expected << 0.16", got[0])

    def test_packages_from_other_repos_are_not_checked(self):
        pk = [{"name": "tetron", "kind": "deb", "version": "0.15.3", "revision": "1"},
              own("b", depends=["tetron (>= 0.15.3)"])]
        self.assertEqual(build.pin_problems(pk), [])

    def test_manifest_passes(self):
        import tomllib
        top = tomllib.loads((Path(build.__file__).parent / "manifest.toml").read_text())
        self.assertEqual(build.pin_problems(top["package"]), [])


class BreaksField(unittest.TestCase):
    def test_breaks_written(self):
        c = build.control(dict(own("b"), arch="all", description="d", breaks=["a (<< 0.15.0-4)"]), "m", 1)
        self.assertIn("Breaks: a (<< 0.15.0-4)\n", c)


def make_zip(path, members):
    """members: (name, mode, data) or (name, "link", target)."""
    import stat, zipfile
    with zipfile.ZipFile(path, "w") as z:
        for name, mode, data in members:
            zi = zipfile.ZipInfo(name)
            if mode == "link":
                zi.external_attr = (stat.S_IFLNK | 0o777) << 16
            else:
                zi.external_attr = (stat.S_IFREG | mode) << 16
            z.writestr(zi, data)


TREE_PKG = {"name": "carbonyl", "version": "0.0.3", "revision": "1", "arch": "amd64",
            "description": "test", "license": "BSD-3-Clause",
            "trees": [{"src": "carbonyl-0.0.3", "dst": "usr/lib/carbonyl"}]}


class ArchiveTrees(unittest.TestCase):
    def stage(self, members):
        import tempfile
        td = tempfile.mkdtemp()
        z = Path(td) / "a.zip"
        make_zip(z, members)
        st = Path(td) / "stage"
        build.extract_trees(TREE_PKG, z, st)
        return st

    def test_copies_files_under_src_with_modes(self):
        st = self.stage([("carbonyl-0.0.3/carbonyl", 0o755, "bin"),
                         ("carbonyl-0.0.3/icudtl.dat", 0o600, "data"),
                         ("carbonyl-0.0.3/sub/x.json", 0o644, "{}"),
                         ("other/ignored", 0o644, "no")])
        d = st / "usr/lib/carbonyl"
        self.assertEqual((d / "carbonyl").stat().st_mode & 0o777, 0o755)
        self.assertEqual((d / "icudtl.dat").stat().st_mode & 0o777, 0o644)
        self.assertEqual((d / "sub/x.json").read_text(), "{}")
        self.assertFalse((st / "other").exists())
        self.assertFalse((d / "other").exists())

    def test_rejects_symlink(self):
        with self.assertRaises(SystemExit):
            self.stage([("carbonyl-0.0.3/a", 0o755, "x"), ("carbonyl-0.0.3/l", "link", "/etc/passwd")])

    def test_rejects_dotdot_and_absolute(self):
        with self.assertRaises(SystemExit):
            self.stage([("carbonyl-0.0.3/../evil", 0o644, "x")])
        with self.assertRaises(SystemExit):
            self.stage([("carbonyl-0.0.3/a", 0o644, "x"), ("/carbonyl-0.0.3/b", 0o644, "x")])

    def test_empty_src_aborts(self):
        with self.assertRaises(SystemExit):
            self.stage([("other/a", 0o644, "x")])


ROOT_PKG = {"name": "font", "version": "1", "revision": "1", "arch": "all",
            "description": "test", "license": "MIT",
            "trees": [{"src": "", "dst": "usr/share/fonts/x", "include": ["*.ttf"]},
                      {"src": "", "dst": "usr/share/doc/font", "include": ["LICENSE"]}]}


class ArchiveRootAndInclude(unittest.TestCase):
    def stage(self, members, pkg=ROOT_PKG):
        import tempfile
        td = tempfile.mkdtemp()
        z = Path(td) / "a.zip"
        make_zip(z, members)
        st = Path(td) / "stage"
        build.extract_trees(pkg, z, st)
        return st

    def test_root_with_include_globs(self):
        st = self.stage([("A.ttf", 0o644, "a"), ("B.ttf", 0o644, "b"), ("LICENSE", 0o644, "MIT"),
                         ("10-x.conf", 0o644, "<xml/>"), ("README.md", 0o644, "r")])
        self.assertEqual(sorted(p.name for p in (st / "usr/share/fonts/x").iterdir()), ["A.ttf", "B.ttf"])
        self.assertEqual([p.name for p in (st / "usr/share/doc/font").iterdir()], ["LICENSE"])

    def test_include_matching_nothing_aborts(self):
        with self.assertRaises(SystemExit):
            self.stage([("README.md", 0o644, "r"), ("LICENSE", 0o644, "MIT")])

    def test_root_still_rejects_dotdot(self):
        with self.assertRaises(SystemExit):
            self.stage([("A.ttf", 0o644, "a"), ("LICENSE", 0o644, "MIT"), ("../evil.ttf", 0o644, "x")])

    def test_copyright_points_to_upstream_license(self):
        self.assertIn("/usr/share/doc/font/LICENSE", build.copyright_text(ROOT_PKG, True))
        self.assertIn("/usr/share/common-licenses/MIT", build.copyright_text(ROOT_PKG))


class Retried(unittest.TestCase):
    def test_transient_errors_are_retried_then_fatal(self):
        calls = []

        def flaky(u):
            calls.append(u)
            if len(calls) < 3:
                raise OSError("HTTP Error 504")
            return "ok"
        self.assertEqual(build.retried("read", "u", flaky, wait=0), "ok")

        def down(u):
            raise OSError("HTTP Error 504")
        with self.assertRaises(SystemExit):
            build.retried("read", "u", down, tries=2, wait=0)


class ListDebs(unittest.TestCase):
    def test_one_file_name_per_manifest_package(self):
        import subprocess, tomllib
        out = subprocess.run([sys.executable, str(build.HERE / "build.py"), "--list-debs"],
                             capture_output=True, text=True, check=True).stdout.split()
        pkgs = tomllib.loads((build.HERE / "manifest.toml").read_text())["package"]
        self.assertEqual(out, [build.deb_filename(p) for p in pkgs])
        self.assertIn("tetron-wm_0.15.6-1_amd64.deb", out)
        self.assertIn("tetron-wm-essentials_0.15.6-1_all.deb", out)
        self.assertIn("tetron-wm-recommended_0.15.6-1_all.deb", out)


class LocalDebs(unittest.TestCase):
    def test_local_deb_is_taken_without_download_and_checked(self):
        import tempfile
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            build.build_one(META, TOP, Path(src), 1792998000)
            rel = dict(META, kind="deb", source={"url": "http://127.0.0.1:9/none.deb", "sha256": "0" * 64})
            got = build.take_release_deb(rel, Path(out), Path(src))
            self.assertEqual(got.read_bytes(), (Path(src) / got.name).read_bytes())
            from unittest import mock
            with mock.patch.object(build, "get_asset", side_effect=SystemExit("download")) as g:
                with self.assertRaises(SystemExit):
                    build.take_release_deb(dict(rel, revision="2"), Path(out), Path(src))
                g.assert_called_once()

    def test_wrong_fields_in_a_local_deb_abort(self):
        import shutil, tempfile
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            deb = build.build_one(META, TOP, Path(src), 1792998000)
            other = dict(META, name="tetronos-server", kind="deb", source={"url": "http://127.0.0.1:9/x", "sha256": "0" * 64})
            shutil.copyfile(deb, Path(src) / build.deb_filename(other))
            with self.assertRaises(SystemExit):
                build.take_release_deb(other, Path(out), Path(src))


if __name__ == "__main__":
    unittest.main()
