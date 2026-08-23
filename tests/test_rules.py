"""The declarativeNetRequest rules under rules/.

These rules run before the page paints, on every hard load of a YouTube URL,
and there is no way to see what they did other than the address bar changing.
That makes them the part of the extension most worth testing away from a
browser: a regex that matches one URL too many sends people somewhere they
didn't ask for, and a rule whose redirect target matches its own condition is
a redirect loop.

The matching here mirrors Chrome's documented behaviour:

* `regexFilter` is matched against the whole URL, unanchored, and is
  case-insensitive unless `isUrlFilterCaseSensitive` says otherwise;
* `regexSubstitution` replaces *the matched portion* of the URL, not the whole
  URL, so anything the pattern doesn't consume survives into the result.

That second point is the one that is easy to get wrong by eye.
"""
import re
import unittest

import support

RULES = support.rules()
SUBS = "https://www.youtube.com/feed/subscriptions"


def matches(rule: dict, url: str) -> bool:
    flags = 0 if rule["condition"].get("isUrlFilterCaseSensitive") else re.I
    return re.search(rule["condition"]["regexFilter"], url, flags) is not None


def apply_rule(rule: dict, url: str) -> str:
    """The URL a matching rule redirects to."""
    redirect = rule["action"]["redirect"]
    if "url" in redirect:
        return redirect["url"]
    flags = 0 if rule["condition"].get("isUrlFilterCaseSensitive") else re.I
    # Chrome's \1 .. \9 back-references, in Python's spelling.
    substitution = re.sub(r"\\(\d)", r"\\g<\1>", redirect["regexSubstitution"])
    return re.sub(rule["condition"]["regexFilter"], substitution, url,
                  count=1, flags=flags)


def redirect_for(url: str) -> str | None:
    """What the whole ruleset does with a URL, or None if nothing matches."""
    hits = [r for r in RULES if matches(r, url)]
    if not hits:
        return None
    # Highest priority wins; the "no two rules match" test keeps ties from
    # ever being load-bearing.
    best = max(hits, key=lambda r: r["priority"])
    return apply_rule(best, url)


class RuleStructure(unittest.TestCase):
    def test_ids_are_unique(self):
        ids = [r["id"] for r in RULES]
        self.assertEqual(len(ids), len(set(ids)), "duplicate rule ids")

    def test_every_rule_is_a_main_frame_redirect(self):
        for rule in RULES:
            with self.subTest(id=rule["id"]):
                self.assertEqual(rule["action"]["type"], "redirect")
                self.assertEqual(rule["condition"]["resourceTypes"], ["main_frame"])
                self.assertIn("priority", rule)

    def test_every_pattern_compiles(self):
        for rule in RULES:
            with self.subTest(id=rule["id"]):
                re.compile(rule["condition"]["regexFilter"])

    def test_patterns_are_anchored_to_youtube(self):
        # An unanchored pattern would match the host anywhere in the URL —
        # including inside a query string on an unrelated site.
        for rule in RULES:
            with self.subTest(id=rule["id"]):
                self.assertTrue(
                    rule["condition"]["regexFilter"].startswith(
                        "^https://www\\.youtube\\.com/"),
                    "rules must be anchored at the YouTube origin")

    def test_static_redirect_targets_are_youtube(self):
        for rule in RULES:
            url = rule["action"]["redirect"].get("url")
            if url:
                with self.subTest(id=rule["id"]):
                    self.assertTrue(url.startswith("https://www.youtube.com/"))


class Homepage(unittest.TestCase):
    def test_bare_homepage_goes_to_subscriptions(self):
        self.assertEqual(redirect_for("https://www.youtube.com/"), SUBS)

    def test_homepage_with_query_goes_to_subscriptions(self):
        # YouTube links to itself with tracking parameters (?gl=, ?app=desktop).
        self.assertEqual(redirect_for("https://www.youtube.com/?gl=GB"), SUBS)

    def test_other_pages_are_left_alone(self):
        for url in (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/results?search_query=cats",
            "https://www.youtube.com/@someone",
            "https://www.youtube.com/playlist?list=PL123",
        ):
            with self.subTest(url=url):
                self.assertIsNone(redirect_for(url))

    def test_other_hosts_are_left_alone(self):
        # host_permissions only covers www.youtube.com; the rules must agree.
        for url in (
            "https://m.youtube.com/",
            "https://music.youtube.com/",
            "https://www.youtube-nocookie.com/",
            "http://www.youtube.com/",
            "https://example.com/?u=https://www.youtube.com/",
        ):
            with self.subTest(url=url):
                self.assertIsNone(redirect_for(url))


class ShortsFeed(unittest.TestCase):
    def test_shorts_feed_goes_to_subscriptions(self):
        for url in (
            "https://www.youtube.com/shorts",
            "https://www.youtube.com/shorts/",
            "https://www.youtube.com/shorts?foo=bar",
        ):
            with self.subTest(url=url):
                self.assertEqual(redirect_for(url), SUBS)


class SingleShort(unittest.TestCase):
    def test_a_short_becomes_a_watch_url(self):
        self.assertEqual(
            redirect_for("https://www.youtube.com/shorts/dQw4w9WgXcQ"),
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_ids_with_dashes_and_underscores_survive(self):
        self.assertEqual(
            redirect_for("https://www.youtube.com/shorts/a-b_c123"),
            "https://www.youtube.com/watch?v=a-b_c123")

    def test_a_shared_short_does_not_keep_its_query_string(self):
        # Shorts are shared as /shorts/<id>?feature=share. regexSubstitution
        # replaces only the part of the URL the pattern matched, so a pattern
        # that stops at the id leaves the original query dangling after the
        # substituted one — ...watch?v=<id>?feature=share, which YouTube reads
        # as an id of "<id>?feature=share" and fails to play.
        for url in (
            "https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ?t=3",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ/",
        ):
            with self.subTest(url=url):
                self.assertEqual(redirect_for(url),
                                 "https://www.youtube.com/watch?v=dQw4w9WgXcQ")


class NoLoops(unittest.TestCase):
    def test_redirect_targets_are_not_themselves_redirected(self):
        # The one failure mode a user cannot recover from: a rule whose output
        # matches a rule's condition, so the browser bounces forever.
        seen = set()
        for rule in RULES:
            url = rule["action"]["redirect"].get("url")
            if url:
                seen.add(url)
        seen.add("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        for url in sorted(seen):
            with self.subTest(url=url):
                self.assertIsNone(redirect_for(url),
                                  f"{url} is a redirect target and also matches a rule")

    def test_no_url_matches_two_rules(self):
        urls = [
            "https://www.youtube.com/",
            "https://www.youtube.com/?gl=GB",
            "https://www.youtube.com/shorts",
            "https://www.youtube.com/shorts/",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share",
        ]
        for url in urls:
            with self.subTest(url=url):
                hits = [r["id"] for r in RULES if matches(r, url)]
                self.assertLessEqual(len(hits), 1,
                                     f"{url} matches rules {hits}; the winner "
                                     "would depend on tie-breaking")


class MatchesTheContentScript(unittest.TestCase):
    """The rulesets and content.js are deliberately redundant, so they have to
    agree: the same URL must end up in the same place whether it was typed
    (network rules) or clicked inside the app (content script)."""

    def test_the_content_script_covers_every_redirect_the_rules_make(self):
        # The destination lives in settings.js now, shared by both halves, so
        # the pair is read together.
        script = support.read("content.js") + support.read("settings.js")
        self.assertIn("/feed/subscriptions", script)
        self.assertIn("/watch?v=", script)
        for path in ("'/'", "'/shorts'", "'/shorts/'"):
            with self.subTest(path=path):
                self.assertIn(path, script)

    def test_each_ruleset_is_named_for_the_one_thing_it_does(self):
        # A ruleset is the unit the menu switches on and off, so two rules in
        # one file would mean two behaviours behind a single switch.
        for name, group in support.rulesets().items():
            with self.subTest(ruleset=name):
                self.assertEqual(len(group), 1)


if __name__ == "__main__":
    unittest.main()
