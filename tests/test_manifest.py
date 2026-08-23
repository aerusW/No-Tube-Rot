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
    """README: no network requests of its own, nothing leaves the machine.

    Every one of those promises is really a promise about this file. A new
    permission is also the one change CONTRIBUTING calls a MAJOR bump, so it
    should never arrive quietly — `storage` arrived in 2.0 and cost one.
    """

    def test_permissions_are_exactly_these_two(self):
        # storage holds the settings, and nothing else. Adding a third entry
        # is a MAJOR bump and a conversation, not a quiet edit.
        self.assertEqual(MANIFEST["permissions"],
                         ["declarativeNetRequest", "storage"])

    def test_no_optional_permissions(self):
        self.assertNotIn("optional_permissions", MANIFEST)
        self.assertNotIn("optional_host_permissions", MANIFEST)

    def test_host_access_is_youtube_only(self):
        self.assertEqual(MANIFEST["host_permissions"], [HOST])

    def test_no_background_worker(self):
        # Still true after 2.0, and worth keeping true: the menu switches the
        # rulesets itself, so nothing needs to run when no YouTube tab is open.
        self.assertNotIn("background", MANIFEST)

    def test_no_remote_code_or_web_accessible_resources(self):
        self.assertNotIn("web_accessible_resources", MANIFEST)
        self.assertNotIn("content_security_policy", MANIFEST)

    def test_the_menu_is_reachable_both_ways(self):
        # 2.0 reversed "installing it is the configuration". With every switch
        # off by default, an unreachable menu is an extension that does nothing
        # at all — so both entry points are load-bearing.
        self.assertEqual(MANIFEST["action"]["default_popup"], "options.html")
        self.assertEqual(MANIFEST["options_ui"]["page"], "options.html")

    def test_both_entry_points_open_the_same_page(self):
        self.assertEqual(MANIFEST["action"]["default_popup"],
                         MANIFEST["options_ui"]["page"])

    def test_no_other_ui_surfaces(self):
        for key in ("browser_action", "page_action", "options_page",
                    "commands", "omnibox"):
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

    def test_it_loads_both_stylesheets_and_both_scripts(self):
        entry = MANIFEST["content_scripts"][0]
        self.assertEqual(entry["css"], ["hide-shorts.css", "calm.css"])
        # settings.js first: content.js reads the schema off it at load time,
        # and a content script list is applied in order.
        self.assertEqual(entry["js"], ["settings.js", "content.js"])


class Packaging(unittest.TestCase):
    def test_manifest_v3(self):
        self.assertEqual(MANIFEST["manifest_version"], 3)

    def test_one_ruleset_per_redirect(self):
        # Splitting them is what lets the menu switch a redirect on without
        # switching on the other two.
        resources = MANIFEST["declarative_net_request"]["rule_resources"]
        self.assertEqual([res["id"] for res in resources],
                         ["redirect-home", "redirect-shorts-feed", "shorts-as-video"])

    def test_every_ruleset_ships_enabled(self):
        # The default position: a fresh install already redirects, with nothing
        # to configure first. A ruleset committed disabled would quietly drop
        # that redirect for everyone who never opens the menu.
        for res in MANIFEST["declarative_net_request"]["rule_resources"]:
            with self.subTest(ruleset=res["id"]):
                self.assertTrue(res["enabled"])

    def test_ruleset_files_live_together_and_exist(self):
        for res in MANIFEST["declarative_net_request"]["rule_resources"]:
            with self.subTest(ruleset=res["id"]):
                self.assertEqual(res["path"], f"rules/{res['id']}.json")
                self.assertTrue((support.ROOT / res["path"]).exists())

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
