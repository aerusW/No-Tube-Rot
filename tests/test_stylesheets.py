"""hide-shorts.css and calm.css.

A stylesheet can only really be judged in a browser, so these tests stay off
the ground the browser owns (does this selector match YouTube's current DOM?)
and cover the things that are true regardless of what YouTube ships this week:

* the files parse and every rule actually declares something;
* hiding rules hide, and beat YouTube's own styles;
* the two theme palettes define the same variables, so a variable added to one
  can't leave the other theme unpainted;
* the colours in those palettes clear WCAG AA, which is the claim calm.css
  makes in its own comments and the reason 1.3.2 existed.
"""
import re
import unittest

import support

HIDE = support.read("hide-shorts.css")
CALM = support.read("calm.css")

VAR_DEF_RE = re.compile(r"(--ntr-[\w-]+)\s*:\s*([^;]+);")
VAR_USE_RE = re.compile(r"var\((--ntr-[\w-]+)\)")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

DARK, LIGHT = "html[dark]", "html:not([dark])"


def palette(selector: str) -> dict[str, str]:
    """The custom properties one theme block defines."""
    for selectors, block in support.css_rules(CALM):
        if selectors == selector:
            return dict(VAR_DEF_RE.findall(block + ";"))
    raise AssertionError(f"no {selector} block in calm.css")


class Structure(unittest.TestCase):
    def test_both_stylesheets_parse(self):
        for name, css in (("hide-shorts.css", HIDE), ("calm.css", CALM)):
            with self.subTest(name=name):
                rules = support.css_rules(css)
                self.assertTrue(rules)
                for selectors, block in rules:
                    self.assertTrue(selectors, f"{name} has a rule with no selector")
                    self.assertTrue(block, f"{name}: '{selectors}' declares nothing")

    def test_declarations_are_terminated(self):
        # A missing semicolon silently swallows the declaration after it.
        for name, css in (("hide-shorts.css", HIDE), ("calm.css", CALM)):
            for selectors, block in support.css_rules(css):
                with self.subTest(name=name, selectors=selectors):
                    self.assertTrue(block.endswith(";"),
                                    f"{name}: '{selectors}' is missing a final ';'")

    def test_no_leftover_debugging_colours(self):
        # Bright primaries are what you leave behind after checking whether a
        # selector matches at all.
        for name, css in (("hide-shorts.css", HIDE), ("calm.css", CALM)):
            body = support.strip_comments(css).lower()
            for smell in ("outline: 1px solid red", "background: lime",
                          "background: magenta", "border: 1px solid red"):
                with self.subTest(name=name, smell=smell):
                    self.assertNotIn(smell, body)


class HideShorts(unittest.TestCase):
    def test_every_rule_hides(self):
        for selectors, block in support.css_rules(HIDE):
            with self.subTest(selectors=selectors):
                decls = support.declarations(block)
                self.assertEqual([p for p, _ in decls], ["display"],
                                 "hide-shorts.css only exists to hide things")
                self.assertEqual(decls[0][1], "none !important",
                                 "YouTube's own display rules are more specific")

    def test_shorts_is_matched_case_insensitively(self):
        # YouTube leaves "Shorts" untranslated but switches between singular
        # and plural, so attribute matching must carry the `i` flag.
        for selectors, _ in support.css_rules(HIDE):
            for attr in re.findall(r'\[\s*(?:title|aria-label|tab-title)\s*[\^*$]?=\s*"[^"]*"[^\]]*\]',
                                   selectors):
                with self.subTest(attr=attr):
                    self.assertRegex(attr, r'"\s+i\s*\]$',
                                     "text attribute matching needs the i flag")

    def test_no_selector_matches_visible_english_text(self):
        # :has(:contains(...)) and friends would break in every other locale.
        body = support.strip_comments(HIDE)
        for banned in (":contains", "::-moz-", "-webkit-any"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, body)

    def test_covers_the_documented_surfaces(self):
        # The README promises these five places specifically.
        body = support.strip_comments(HIDE)
        for hook, surface in (
            ("ytd-rich-shelf-renderer[is-shorts]", "home / subscriptions shelf"),
            ("grid-shelf-view-model", "search results shelf"),
            ("ytd-guide-entry-renderer", "left sidebar"),
            ("ytd-mini-guide-entry-renderer", "collapsed mini sidebar"),
            ("yt-tab-shape", "channel page tab"),
        ):
            with self.subTest(surface=surface):
                self.assertIn(hook, body)


class Palettes(unittest.TestCase):
    def test_both_themes_define_the_same_variables(self):
        dark, light = palette(DARK), palette(LIGHT)
        self.assertEqual(sorted(dark), sorted(light),
                         "a variable defined in one theme only leaves the other "
                         "theme unpainted")

    def test_every_variable_used_is_defined(self):
        used = set(VAR_USE_RE.findall(support.strip_comments(CALM)))
        defined = set(palette(DARK))
        self.assertEqual(used - defined, set(),
                         "calm.css uses variables no palette defines")

    def test_every_variable_defined_is_used_or_reserved(self):
        # Two slots are held for the surfaces they name rather than read today.
        # They stay in both palettes, and the contrast tests below hold them to
        # the same bar as the rest, so the first rule that uses one is already
        # known to be legible.
        reserved = {"--ntr-surface-2", "--ntr-dim"}
        used = set(VAR_USE_RE.findall(support.strip_comments(CALM)))
        defined = set(palette(DARK))
        self.assertEqual(defined - used - reserved, set(),
                         "calm.css defines variables nothing reads")

    def test_text_colour_is_only_set_where_the_surface_is(self):
        # 1.3.2: the restyle forced its own text colours regardless of
        # YouTube's theme, so a light-theme YouTube got dark text on dark
        # surfaces. The rule that came out of it: only repaint text where this
        # stylesheet also repaints what sits behind it.
        for selectors, block in support.css_rules(CALM):
            if selectors in (DARK, LIGHT):
                continue
            props = [p for p, _ in support.declarations(block)]
            if "color" in props:
                with self.subTest(selectors=selectors):
                    self.assertTrue(
                        any(p.startswith("background") for p in props),
                        f"'{selectors}' sets text colour without setting the "
                        "surface under it")


class Contrast(unittest.TestCase):
    """WCAG AA is 4.5:1 for body text, 3:1 for large text and UI edges."""

    def each_theme(self):
        yield "dark", palette(DARK)
        yield "light", palette(LIGHT)

    def test_colours_are_six_digit_hex(self):
        # rgba() is used for borders on purpose; everything the contrast maths
        # reads has to be opaque.
        for theme, colours in self.each_theme():
            for name in ("--ntr-bg", "--ntr-surface", "--ntr-surface-2",
                         "--ntr-text", "--ntr-dim", "--ntr-accent",
                         "--ntr-on-accent"):
                with self.subTest(theme=theme, name=name):
                    self.assertRegex(colours[name].split()[0], HEX_RE.pattern)

    def test_text_on_every_surface(self):
        for theme, c in self.each_theme():
            for surface in ("--ntr-bg", "--ntr-surface", "--ntr-surface-2"):
                with self.subTest(theme=theme, surface=surface):
                    self.assertGreaterEqual(
                        support.contrast_ratio(c["--ntr-text"], c[surface]), 4.5)

    def test_dim_text_on_the_background(self):
        for theme, c in self.each_theme():
            with self.subTest(theme=theme):
                self.assertGreaterEqual(
                    support.contrast_ratio(c["--ntr-dim"], c["--ntr-bg"]), 4.5)

    def test_text_on_the_accent(self):
        # Selected chips and the notification badge put text on the accent.
        for theme, c in self.each_theme():
            with self.subTest(theme=theme):
                self.assertGreaterEqual(
                    support.contrast_ratio(c["--ntr-on-accent"], c["--ntr-accent"]), 4.5)

    def test_the_accent_is_visible_against_the_background(self):
        # The scrubber and progress bar are UI, not text: 3:1.
        for theme, c in self.each_theme():
            with self.subTest(theme=theme):
                self.assertGreaterEqual(
                    support.contrast_ratio(c["--ntr-accent"], c["--ntr-bg"]), 3.0)

    def test_the_accent_is_not_youtube_red(self):
        # The whole point of the restyle.
        for theme, c in self.each_theme():
            with self.subTest(theme=theme):
                self.assertNotIn(c["--ntr-accent"].lower(),
                                 ("#ff0000", "#f00", "#cc0000", "#ff0033"))


if __name__ == "__main__":
    unittest.main()
