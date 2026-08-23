"""release_notes.py — the GitHub release body.

The release workflow pipes this straight into `gh release create --notes-file`,
after the .xpi has already been signed. A wrong answer here is discovered at
the last step of a release that cannot be re-run under the same version, so
the extraction is worth pinning down: the right section, all of it, and
nothing from the section below it.

The last group of tests runs against the repository's real CHANGELOG.md, so
every version that could still be tagged is known to produce notes.
"""
import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

import support

FIXTURE = """# Changelog

Preamble that belongs to no version.

## 2.0.0 — 2026-03-01

### Added

* The newest thing.

## 1.9.0 — 2026-02-01

### Changed

* Something in the middle.

## 1.8.0 — 2026-01-01

### Fixed

* The oldest thing, with nothing after it.
"""


class NotesCase(unittest.TestCase):
    def setUp(self):
        self.notes = support.load_script("release_notes")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        original = self.notes.ROOT
        self.notes.ROOT = self.root
        self.addCleanup(setattr, self.notes, "ROOT", original)
        (self.root / "CHANGELOG.md").write_text(FIXTURE, encoding="utf-8")


class Extraction(NotesCase):
    def test_the_newest_section_stops_before_the_next_heading(self):
        body = self.notes.notes_for("2.0.0")
        self.assertIn("The newest thing.", body)
        self.assertNotIn("1.9.0", body)
        self.assertNotIn("Something in the middle.", body)

    def test_a_middle_section_is_bounded_on_both_sides(self):
        body = self.notes.notes_for("1.9.0")
        self.assertIn("Something in the middle.", body)
        self.assertNotIn("The newest thing.", body)
        self.assertNotIn("The oldest thing", body)

    def test_the_last_section_runs_to_the_end_of_the_file(self):
        body = self.notes.notes_for("1.8.0")
        self.assertIn("The oldest thing, with nothing after it.", body)

    def test_the_heading_itself_is_not_repeated_in_the_body(self):
        # gh puts the tag on the release already.
        self.assertNotIn("## 2.0.0", self.notes.notes_for("2.0.0"))

    def test_the_preamble_is_not_included(self):
        for version in ("2.0.0", "1.9.0", "1.8.0"):
            with self.subTest(version=version):
                self.assertNotIn("Preamble", self.notes.notes_for(version))

    def test_an_unknown_version_returns_none(self):
        self.assertIsNone(self.notes.notes_for("3.0.0"))

    def test_a_partial_version_is_not_a_match(self):
        # "1.9" must not quietly resolve to the 1.9.0 section.
        self.assertIsNone(self.notes.notes_for("1.9"))


class CommandLine(NotesCase):
    def run_main(self, *argv) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        original = sys.argv
        sys.argv = ["release_notes.py", *argv]
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = self.notes.main()
        finally:
            sys.argv = original
        return code, out.getvalue(), err.getvalue()

    def test_it_prints_the_section_and_exits_zero(self):
        code, out, _ = self.run_main("1.9.0")
        self.assertEqual(code, 0)
        self.assertIn("Something in the middle.", out)

    def test_an_unknown_version_fails_loudly(self):
        code, out, err = self.run_main("3.0.0")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("3.0.0", err)

    def test_no_arguments_is_a_usage_error(self):
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("release_notes.py", err)


class TheRealChangelog(unittest.TestCase):
    def setUp(self):
        self.notes = support.load_script("release_notes")
        self.checks = support.load_script("checks")
        self.versions = [v for v, _ in self.checks.CHANGELOG_HEADING.findall(
            support.read("CHANGELOG.md"))]

    def test_every_released_version_has_notes(self):
        # Any of these tags can be checked out and re-released.
        self.assertTrue(self.versions)
        for version in self.versions:
            with self.subTest(version=version):
                body = self.notes.notes_for(version)
                self.assertIsNotNone(body)
                self.assertTrue(body.strip(), f"{version} has an empty section")

    def test_the_current_version_has_notes(self):
        self.assertIsNotNone(self.notes.notes_for(support.manifest()["version"]))

    def test_every_section_can_actually_be_printed(self):
        # notes_for() returning a string is not the same as main() being able
        # to write it: a Windows console defaults to a legacy code page, and
        # 2.0.0's release note opens with a ⚠️ callout that cannot be encoded
        # in it. That crashed the script on the machine CONTRIBUTING tells
        # contributors to rehearse a release from.
        import subprocess
        for version in self.versions:
            with self.subTest(version=version):
                result = subprocess.run(
                    [sys.executable, str(support.ROOT / ".github" / "scripts"
                                         / "release_notes.py"), version],
                    capture_output=True, cwd=support.ROOT)
                self.assertEqual(result.returncode, 0,
                                 result.stderr.decode("utf-8", "replace"))
                self.assertTrue(result.stdout.decode("utf-8").strip())

    def test_versions_are_newest_first(self):
        as_tuples = [tuple(int(p) for p in v.split(".")) for v in self.versions]
        self.assertEqual(as_tuples, sorted(as_tuples, reverse=True),
                         "CHANGELOG.md is newest-first")

    def test_dates_never_go_backwards(self):
        dates = [d for _, d in self.checks.CHANGELOG_HEADING.findall(
            support.read("CHANGELOG.md"))]
        self.assertEqual(dates, sorted(dates, reverse=True),
                         "a release is dated before the one it follows")


if __name__ == "__main__":
    unittest.main()
