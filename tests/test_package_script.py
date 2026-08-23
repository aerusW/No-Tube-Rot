"""package.py — the release archive.

This script exists because of issue #1: the add-on looked broken on Firefox
for months, and the actual cause was a generated `_metadata/` directory that
Chrome had written into the folder being packaged. The fix was to build the
archive from an allowlist derived from manifest.json instead of sweeping up
the working tree.

So the test that matters most here is the boring-looking one: put junk in the
tree, and check none of it comes out in the package.
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
import zipfile

import support


class PackageCase(unittest.TestCase):
    def setUp(self):
        self.package = support.load_script("package")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        for name, value in (("ROOT", self.root),
                            ("DIST", self.root / "dist"),
                            ("STAGING", self.root / "dist" / "staging")):
            original = getattr(self.package, name)
            setattr(self.package, name, value)
            self.addCleanup(setattr, self.package, name, original)

    def build(self, **kwargs) -> tuple[int, str]:
        support.build_fixture(self.root, **kwargs)
        return self.run_package()

    def run_package(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.package.main()
        return code, out.getvalue()

    def archived(self) -> set[str]:
        archives = list((self.root / "dist").glob("*.zip"))
        self.assertEqual(len(archives), 1, "expected exactly one archive")
        with zipfile.ZipFile(archives[0]) as z:
            return set(z.namelist())

    def staged(self) -> set[str]:
        staging = self.root / "dist" / "staging"
        return {p.relative_to(staging).as_posix()
                for p in staging.rglob("*") if p.is_file()}


class WhatShips(PackageCase):
    EXPECTED = {"manifest.json", "LICENSE", "rules/redirect-home.json",
                "settings.js", "content.js", "calm.css", "icons/icon-16.png",
                "options.html", "options.css", "options.js"}

    def test_it_packages_exactly_the_manifest_plus_the_always_list(self):
        code, _ = self.build()
        self.assertEqual(code, 0)
        self.assertEqual(self.archived(), self.EXPECTED)

    def test_the_menu_ships_with_the_files_it_loads(self):
        # The manifest names options.html and nothing else about the menu;
        # options.css and options.js reach the archive only because the
        # allowlist follows the page into them.
        self.build()
        for rel in ("options.html", "options.css", "options.js"):
            with self.subTest(rel=rel):
                self.assertIn(rel, self.archived())

    def test_a_missing_menu_asset_stops_the_build(self):
        # The failure this guards against ships an extension whose menu opens
        # blank — and with everything off by default, that is an extension
        # that cannot be turned on at all.
        code, out = self.build(drop=("options.js",))
        self.assertEqual(code, 1)
        self.assertIn("options.js", out)

    def test_nested_paths_survive_the_archive(self):
        self.build()
        self.assertIn("rules/redirect-home.json", self.archived())

    def test_the_staging_tree_and_the_archive_agree(self):
        # The release workflow signs the staging directory and ships the zip;
        # if they ever differ, Firefox and Chrome users get different code.
        self.build()
        self.assertEqual(self.staged(), self.archived())

    def test_the_archive_is_named_for_the_manifest_version(self):
        self.build(version="2.3.4")
        self.assertTrue((self.root / "dist" / "no-tube-rot-2.3.4.zip").exists())

    def test_the_licence_ships_even_though_nothing_references_it(self):
        self.build()
        self.assertIn("LICENSE", self.package.ALWAYS)
        self.assertIn("manifest.json", self.package.ALWAYS)


class WhatDoesNot(PackageCase):
    def test_generated_and_untracked_files_are_left_out(self):
        # Everything here has been in this repository's working tree at some
        # point. `_metadata/` is the one that cost months.
        support.build_fixture(self.root)
        junk = {
            "_metadata/verified_contents.json",
            "__pycache__/checks.cpython-312.pyc",
            "README.md",
            "CHANGELOG.md",
            ".gitignore",
            "docs/before-home.jpg",
            "notes.txt",
            "key.pem",
        }
        for rel in junk:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("junk", encoding="utf-8")
        self.run_package()

        packaged = self.archived() | self.staged()
        for rel in junk:
            with self.subTest(rel=rel):
                self.assertNotIn(rel, packaged)

    def test_no_packaged_path_starts_with_an_underscore(self):
        # The rule Firefox actually enforces, checked directly rather than by
        # naming the files we happen to know about.
        self.build()
        for rel in self.archived():
            for part in rel.split("/"):
                with self.subTest(rel=rel):
                    self.assertFalse(part.startswith("_"),
                                     "Firefox rejects reserved underscore names")


class Refusals(PackageCase):
    def test_a_missing_referenced_file_stops_the_build(self):
        code, out = self.build(drop=("calm.css",))
        self.assertEqual(code, 1)
        self.assertIn("calm.css", out)

    def test_nothing_is_written_when_it_refuses(self):
        self.build(drop=("calm.css",))
        self.assertFalse((self.root / "dist").exists(),
                         "a refused build must not leave a half-made release")


class Rebuilds(PackageCase):
    def test_a_stale_file_from_a_previous_build_is_cleared(self):
        self.build()
        stale = self.root / "dist" / "staging" / "leftover.js"
        stale.write_text("// from an older build\n", encoding="utf-8")
        self.run_package()
        self.assertNotIn("leftover.js", self.staged())

    def test_the_version_in_the_package_is_the_version_in_the_manifest(self):
        self.build(version="9.9.9")
        with zipfile.ZipFile(self.root / "dist" / "no-tube-rot-9.9.9.zip") as z:
            shipped = json.loads(z.read("manifest.json"))
        self.assertEqual(shipped["version"], "9.9.9")


if __name__ == "__main__":
    unittest.main()
