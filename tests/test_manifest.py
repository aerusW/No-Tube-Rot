"""manifest.json, and the promises the rest of the repository makes about it.

checks.py already gates the mechanical things (the file parses, everything it
references exists, the version is well formed). These tests cover what it
doesn't: the permission surface, which is the project's headline promise, and
the details that only bite at install time — the run_at that decides whether
the redirect beats the first paint, the Firefox id without which no signed
.xpi exists, and icons that are the size they claim.
"""
import struct
import unittest

import support

MANIFEST = support.manifest()
HOST = "*://www.youtube.com/*"


def png_size(rel: str) -> tuple[int, int]:
    """(width, height) from a PNG's IHDR chunk."""
    blob = (support.ROOT / rel).read_bytes()
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{rel} is not a PNG")
    return struct.unpack(">II", blob[16:24])


class Permissions(unittest.TestCase):
    """README: no network requests of its own, no storage, no analytics.

    Every one of those promises is really a promise about this file. A new
    permission is also the one change CONTRIBUTING calls a MAJOR bump, so it
    should never arrive quietly.
    """

    def test_permissions_are_exactly_declarative_net_request(self):
        self.assertEqual(MANIFEST["permissions"], ["declarativeNetRequest"])

    def test_no_optional_permissions(self):
        self.assertNotIn("optional_permissions", MANIFEST)
        self.assertNotIn("optional_host_permissions", MANIFEST)

    def test_host_access_is_youtube_only(self):
        self.assertEqual(MANIFEST["host_permissions"], [HOST])

    def test_no_background_worker(self):
        self.assertNotIn("background", MANIFEST)

    def test_no_remote_code_or_web_accessible_resources(self):
        self.assertNotIn("web_accessible_resources", MANIFEST)
        self.assertNotIn("content_security_policy", MANIFEST)

    def test_no_ui_surfaces(self):
        # "Installing it is the configuration" — no popup, no options page.
        for key in ("action", "browser_action", "page_action", "options_page",
                    "options_ui", "commands", "omnibox"):
            with self.subTest(key=key):
                self.assertNotIn(key, MANIFEST)


class ContentScripts(unittest.TestCase):
    def test_one_content_script_entry(self):
        self.assertEqual(len(MANIFEST["content_scripts"]), 1)

    def test_it_runs_only_on_youtube(self):
        self.assertEqual(MANIFEST["content_scripts"][0]["matches"], [HOST])

    def test_it_runs_at_document_start(self):
        # The SPA redirect has to fire before YouTube's own router does, and
        # the stylesheets have to be in place before the first paint or the
        # Shorts shelves flash up and then vanish.
        self.assertEqual(MANIFEST["content_scripts"][0]["run_at"], "document_start")

    def test_it_loads_both_stylesheets_and_the_script(self):
        entry = MANIFEST["content_scripts"][0]
        self.assertEqual(entry["css"], ["hide-shorts.css", "calm.css"])
        self.assertEqual(entry["js"], ["content.js"])


class Packaging(unittest.TestCase):
    def test_manifest_v3(self):
        self.assertEqual(MANIFEST["manifest_version"], 3)

    def test_the_ruleset_is_registered_and_enabled(self):
        resources = MANIFEST["declarative_net_request"]["rule_resources"]
        self.assertEqual(len(resources), 1)
        self.assertTrue(resources[0]["enabled"])
        self.assertEqual(resources[0]["path"], "rules.json")

    def test_firefox_can_be_signed(self):
        # No gecko id means web-ext sign has nothing to sign against, and the
        # add-on cannot be installed permanently on Firefox at all.
        gecko = MANIFEST["browser_specific_settings"]["gecko"]
        self.assertTrue(gecko["id"])
        self.assertRegex(gecko["strict_min_version"], r"^\d+\.\d+$")

    def test_icons_are_the_size_they_claim(self):
        for size, rel in MANIFEST["icons"].items():
            with self.subTest(size=size):
                self.assertEqual(png_size(rel), (int(size), int(size)))

    def test_every_shipped_file_is_reachable_from_the_manifest(self):
        # package.py builds a release from exactly this list, so a shipped file
        # the manifest doesn't mention would simply not be in the package.
        checks = support.load_script("checks")
        referenced = set(checks.referenced_files(MANIFEST)) | {"manifest.json"}
        for rel in support.SHIPPED:
            with self.subTest(rel=rel):
                self.assertIn(rel, referenced)


class Documentation(unittest.TestCase):
    """The docs quote the manifest; keep them from drifting apart."""

    def test_the_readme_lists_every_permission(self):
        readme = support.read("README.md")
        for permission in MANIFEST["permissions"]:
            with self.subTest(permission=permission):
                self.assertIn(permission, readme)

    def test_the_changelog_leads_with_the_current_version(self):
        checks = support.load_script("checks")
        headings = checks.CHANGELOG_HEADING.findall(support.read("CHANGELOG.md"))
        self.assertEqual(headings[0][0], MANIFEST["version"])


if __name__ == "__main__":
    unittest.main()
