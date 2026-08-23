"""checks.py — the CI gate.

A gate that passes everything is worse than no gate, because it reads as
evidence. Each test here hands checks.py a repository that is broken in one
specific way and asserts that it says so; one test hands it a healthy
repository and asserts it stays quiet.

Every case runs against a throwaway fixture tree, never the real repository.
"""
import contextlib
import io
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

import support


class CheckCase(unittest.TestCase):
    """A temporary repository with checks.py pointed at it."""

    def setUp(self):
        self.checks = support.load_script("checks")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        original = self.checks.ROOT
        self.checks.ROOT = self.root
        self.addCleanup(setattr, self.checks, "ROOT", original)

    def fixture(self, **kwargs) -> pathlib.Path:
        return support.build_fixture(self.root, **kwargs)

    def run_checks(self, *argv) -> tuple[int, str]:
        out = io.StringIO()
        original_argv = sys.argv
        sys.argv = ["checks.py", *argv]
        try:
            with contextlib.redirect_stdout(out):
                code = self.checks.main()
        finally:
            sys.argv = original_argv
        return code, out.getvalue()

    def assertPasses(self):
        code, out = self.run_checks()
        self.assertEqual(code, 0, out)
        self.assertIn("All checks passed", out)

    def assertFails(self, fragment: str):
        code, out = self.run_checks()
        self.assertEqual(code, 1, out)
        self.assertIn(fragment, out)


class HealthyRepository(CheckCase):
    def test_a_clean_tree_passes(self):
        self.fixture()
        self.assertPasses()

    def test_running_twice_gives_the_same_answer(self):
        # Failures accumulate in module state; a second run must not inherit
        # the first one's verdict.
        self.fixture()
        self.assertPasses()
        self.assertPasses()


class BrokenJson(CheckCase):
    def test_unparseable_rules_are_caught(self):
        # The ruleset list is read from the manifest rather than hardcoded, so
        # a redirect added later is parsed too.
        self.fixture()
        (self.root / "rules" / "redirect-home.json").write_text(
            "[{,]", encoding="utf-8")
        self.assertFails("rules/redirect-home.json")

    def test_unparseable_manifest_is_caught(self):
        self.fixture()
        (self.root / "manifest.json").write_text("{", encoding="utf-8")
        self.assertFails("manifest.json")


class Manifest(CheckCase):
    def test_a_missing_required_field_is_caught(self):
        self.fixture()
        import json
        data = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        del data["description"]
        (self.root / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
        self.assertFails("missing 'description'")

    def test_a_referenced_file_that_does_not_exist_is_caught(self):
        self.fixture(drop=("calm.css",))
        self.assertFails("references missing file: calm.css")

    def test_a_two_component_version_is_caught(self):
        # Chrome accepts 1.2; this project does not.
        self.fixture(version="1.2")
        self.assertFails("is not MAJOR.MINOR.PATCH")

    def test_a_four_component_version_is_caught(self):
        self.fixture(version="1.2.3.4")
        self.assertFails("is not MAJOR.MINOR.PATCH")


class Changelog(CheckCase):
    def test_a_changelog_behind_the_manifest_is_caught(self):
        self.fixture(version="1.1.0")
        self.assertFails("newest CHANGELOG entry is 1.0.0")

    def test_a_changelog_with_no_versions_is_caught(self):
        self.fixture(changelog="# Changelog\n\nNothing yet.\n")
        self.assertFails("no '## X.Y.Z")

    def test_a_duplicated_version_is_caught(self):
        self.fixture(changelog=(
            "# Changelog\n\n"
            "## 1.0.0 — 2026-01-02\n\nA second entry.\n\n"
            "## 1.0.0 — 2026-01-01\n\nThe first one.\n"))
        self.assertFails("duplicate CHANGELOG entries for: 1.0.0")

    def test_a_heading_without_a_date_is_not_counted(self):
        self.fixture(changelog="# Changelog\n\n## 1.0.0\n\nNo date.\n")
        self.assertFails("no '## X.Y.Z")


class DebugLeftovers(CheckCase):
    def test_console_log_is_caught(self):
        self.fixture(content_js="console.log('here');\n")
        self.assertFails("content.js contains 'console.log'")

    def test_debugger_is_caught(self):
        self.fixture(content_js="debugger;\n")
        self.assertFails("content.js contains 'debugger'")

    def test_a_failing_file_is_not_also_reported_as_ok(self):
        self.fixture(content_js="console.log('here');\n")
        _, out = self.run_checks()
        self.assertNotIn("ok    content.js", out)


class ReservedNames(CheckCase):
    """Issue #1: a folder containing an underscore-prefixed entry will not load
    in Firefox at all. Chrome writes `_metadata/` into any folder it loads
    unpacked and Python writes `__pycache__/`, so the same tree is routinely
    both fine (in Chrome) and unloadable (in Firefox).

    Generated ones warn — they are the price of a supported workflow, and they
    cannot reach a package. A committed one fails.
    """

    def make(self, rel: str):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated\n", encoding="utf-8")

    def test_a_generated_directory_warns_without_failing(self):
        self.fixture()
        self.make("_metadata/verified_contents.json")
        code, out = self.run_checks()
        self.assertEqual(code, 0, out)
        self.assertIn("warn  _metadata", out)
        self.assertIn("will not load in Firefox", out)

    def test_pycache_is_reported_too(self):
        self.fixture()
        self.make("__pycache__/checks.cpython-312.pyc")
        _, out = self.run_checks()
        self.assertIn("__pycache__", out)

    def test_nested_names_are_reported_by_their_top_directory(self):
        # One line per offending folder, not one per file inside it.
        self.fixture()
        for name in ("a.json", "b.json", "sub/c.json"):
            self.make(f"_metadata/{name}")
        _, out = self.run_checks()
        self.assertEqual(out.count("warn  _metadata"), 1)

    def test_a_clean_tree_says_so(self):
        self.fixture()
        _, out = self.run_checks()
        self.assertIn("nothing Firefox would reject", out)

    def test_dist_and_git_are_not_searched(self):
        # Build output is not what a browser loads, and .git is neither loaded
        # nor cheap to walk.
        self.fixture()
        (self.root / "dist" / "staging" / "_metadata").mkdir(parents=True)
        (self.root / ".git" / "objects" / "_x").mkdir(parents=True)
        self.assertPasses()


@unittest.skipIf(shutil.which("git") is None, "git is not installed")
class ReservedNamesUnderGit(CheckCase):
    def setUp(self):
        super().setUp()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.root, check=True)

    def test_an_ignored_one_only_warns(self):
        self.fixture()
        (self.root / ".gitignore").write_text("_metadata/\n", encoding="utf-8")
        (self.root / "_metadata").mkdir()
        (self.root / "_metadata" / "x.json").write_text("{}", encoding="utf-8")
        code, out = self.run_checks()
        self.assertEqual(code, 0, out)
        self.assertIn("warn  _metadata", out)

    def test_one_that_is_not_ignored_fails(self):
        # Nothing stops it being committed, and then every Firefox user has it.
        self.fixture()
        (self.root / ".gitignore").write_text("dist/\n", encoding="utf-8")
        (self.root / "_metadata").mkdir()
        (self.root / "_metadata" / "x.json").write_text("{}", encoding="utf-8")
        self.assertFails("_metadata is committed")


@unittest.skipIf(shutil.which("git") is None, "git is not installed")
class VersionBump(CheckCase):
    """The rule that a released version is never reused. AMO enforces it too,
    by refusing to sign a version it has already seen — but by then the tag is
    pushed and the release has failed halfway through."""

    def git(self, *args) -> str:
        result = subprocess.run(
            ["git", "-c", "user.email=tests@example.com", "-c", "user.name=Tests",
             "-c", "commit.gpgsign=false", *args],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def commit_fixture(self, version: str, message: str, changelog: str | None = None):
        self.fixture(version=version, changelog=changelog)
        self.git("add", "-A")
        self.git("commit", "-m", message)

    def setUp(self):
        super().setUp()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.root, check=True)

    def test_an_unchanged_version_is_fine(self):
        self.commit_fixture("1.0.0", "first")
        base = self.git("rev-parse", "HEAD")
        (self.root / "README.md").write_text("docs only\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-m", "docs")
        code, out = self.run_checks("--base", base)
        self.assertEqual(code, 0, out)
        self.assertIn("version unchanged at 1.0.0", out)

    def test_a_fresh_bump_is_fine(self):
        self.commit_fixture("1.0.0", "first")
        base = self.git("rev-parse", "HEAD")
        self.commit_fixture("1.0.1", "fix", changelog=(
            "# Changelog\n\n## 1.0.1 — 2026-01-02\n\n### Fixed\n\n* A thing.\n"))
        code, out = self.run_checks("--base", base)
        self.assertEqual(code, 0, out)
        self.assertIn("1.0.0 -> 1.0.1", out)

    def test_bumping_onto_an_existing_tag_is_caught(self):
        self.commit_fixture("1.0.0", "first")
        base = self.git("rev-parse", "HEAD")
        self.commit_fixture("1.0.1", "released", changelog=(
            "# Changelog\n\n## 1.0.1 — 2026-01-02\n\n### Fixed\n\n* A thing.\n"))
        self.git("tag", "-a", "v1.0.1", "-m", "v1.0.1")
        # Someone now writes a different commit claiming the same version.
        (self.root / "content.js").write_text("// different\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-m", "another change under 1.0.1")
        code, out = self.run_checks("--base", base)
        self.assertEqual(code, 1, out)
        self.assertIn("tag v1.0.1 already exists", out)

    def test_an_unreadable_base_is_skipped_not_failed(self):
        # Shallow clones and first pushes have no usable base ref.
        self.commit_fixture("1.0.0", "first")
        code, out = self.run_checks("--base", "0" * 40)
        self.assertEqual(code, 0, out)
        self.assertIn("skip", out)


class SharedHelpers(unittest.TestCase):
    """referenced_files() lives in checks.py but is the allowlist package.py
    builds a release from. It has to see every kind of file the manifest can
    point at, or a release ships without one."""

    def setUp(self):
        self.checks = support.load_script("checks")

    def test_it_finds_icons_scripts_stylesheets_and_rulesets(self):
        found = self.checks.referenced_files(support.manifest())
        for rel in ("icons/icon-16.png", "icons/icon-48.png", "icons/icon-128.png",
                    "hide-shorts.css", "calm.css", "settings.js", "content.js",
                    "rules/redirect-home.json", "rules/redirect-shorts-feed.json",
                    "rules/shorts-as-video.json"):
            with self.subTest(rel=rel):
                self.assertIn(rel, found)

    def test_it_finds_the_menu_and_what_the_menu_loads(self):
        # options.css and options.js are named nowhere in the manifest. Left
        # out of the allowlist, the release ships a menu that opens blank.
        found = self.checks.referenced_files(support.manifest())
        for rel in ("options.html", "options.css", "options.js"):
            with self.subTest(rel=rel):
                self.assertIn(rel, found)

    def test_it_reads_html_from_the_tree_it_is_given(self):
        # package.py points this at the tree being packaged, not at the
        # repository the script happens to live in.
        manifest = {"options_ui": {"page": "page.html"}}
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "page.html").write_text(
                '<link rel="stylesheet" href="only-here.css">', encoding="utf-8")
            self.assertEqual(self.checks.referenced_files(manifest, root),
                             ["page.html", "only-here.css"])
        # Without a root it reads the repository, where that page is absent —
        # an unreadable page is skipped rather than crashing the build.
        self.assertEqual(self.checks.referenced_files(manifest), ["page.html"])

    def test_it_ignores_remote_and_absolute_urls_in_html(self):
        self.assertEqual(self.checks.local_assets(
            '<link href="https://cdn.example/a.css">'
            '<script src="//example/b.js"></script>'
            '<a href="#top">t</a><img src="/abs.png">'
            '<script src="local.js"></script>'), ["local.js"])

    def test_it_does_not_list_a_file_twice(self):
        # The same icons appear under both "icons" and the action; a duplicate
        # would be copied twice and shown twice in the packaging output.
        found = self.checks.referenced_files(support.manifest())
        self.assertEqual(len(found), len(set(found)))

    def test_it_skips_empty_paths_rather_than_returning_them(self):
        self.assertEqual(self.checks.referenced_files(
            {"declarative_net_request": {"rule_resources": [{"id": "x"}]}}), [])

    def test_an_empty_manifest_yields_nothing(self):
        self.assertEqual(self.checks.referenced_files({}), [])

    def test_it_reads_every_content_script_entry(self):
        found = self.checks.referenced_files({"content_scripts": [
            {"css": ["a.css"], "js": ["a.js"]},
            {"css": ["b.css"]},
            {"js": ["b.js"]},
        ]})
        self.assertEqual(found, ["a.css", "a.js", "b.css", "b.js"])


if __name__ == "__main__":
    unittest.main()
