"""hide-shorts.css, calm.css, and the menu's own options.css.

A stylesheet can only really be judged in a browser, so these tests stay off
the ground the browser owns (does this selector match YouTube's current DOM?)
and cover the things that are true regardless of what YouTube ships this week:

* the files parse and every rule actually declares something;
* hiding rules hide, and beat YouTube's own styles;
* **every painting rule is gated behind a switch.** This is the 2.0 promise
  expressed in CSS: an ungated rule would apply on a fresh install, to someone
  who turned nothing on;
* the gate attributes are exactly the ones settings.js sets, so a typo cannot
  leave a switch wired to nothing;
* the two theme palettes define the same variables, so a variable added to one
  can't leave the other theme unpainted;
* every accent clears WCAG AA in both themes, and the swatch the menu shows
  for it is the colour the page will actually use.
"""
import re
import unittest

import support

HIDE = support.read("hide-shorts.css")
CALM = support.read("calm.css")
OPTIONS = support.read("options.css")
SETTINGS = support.read("settings.js")

VAR_DEF_RE = re.compile(r"(--ntr-[\w-]+)\s*:\s*([^;]+);")
VAR_USE_RE = re.compile(r"var\((--ntr-[\w-]+)\)")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# The gate attributes, from each side of the wiring.
CSS_GATE_RE = re.compile(r"\[(data-ntr-[\w-]+)\]")
JS_GATE_RE = re.compile(r"'(data-ntr-[\w-]+)'")
JS_ACCENT_RE = re.compile(r"const ACCENTS = \[([^\]]*)\]")

# .swatch[data-accent="sage"] { background: #4f7a73; }
SWATCH_RE = re.compile(r'\.swatch\[data-accent="(\w+)"\]\s*\{\s*background:\s*(#[0-9a-f]{6})',
                       re.I)

DARK, LIGHT = "html[dark]", "html:not([dark])"
ACCENT_SELECTOR_RE = re.compile(
    r'^html(\[dark\]|:not\(\[dark\]\))\[data-ntr-accent="(\w+)"\]$')


def accents() -> list[str]:
    """The accent names settings.js offers."""
    inner = JS_ACCENT_RE.search(SETTINGS).group(1)
    return re.findall(r"'(\w+)'", inner)


def palette(selector: str) -> dict[str, str]:
    """The custom properties one block defines."""
    for selectors, block in support.css_rules(CALM):
        if selectors == selector:
            return dict(VAR_DEF_RE.findall(block + ";"))
    raise AssertionError(f"no {selector} block in calm.css")


def accent_palette(theme: str, name: str) -> dict[str, str]:
    prefix = "html[dark]" if theme == "dark" else "html:not([dark])"
    return palette(f'{prefix}[data-ntr-accent="{name}"]')


def is_palette_block(selectors: str) -> bool:
    """True for the blocks that only define variables and paint nothing."""
    return selectors in (DARK, LIGHT) or bool(ACCENT_SELECTOR_RE.match(selectors))


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
        for name, css in (("hide-shorts.css", HIDE), ("calm.css", CALM),
                          ("options.css", OPTIONS)):
            body = support.strip_comments(css).lower()
            for smell in ("outline: 1px solid red", "background: lime",
                          "background: magenta", "border: 1px solid red"):
                with self.subTest(name=name, smell=smell):
                    self.assertNotIn(smell, body)


class EverythingAppliesUntilItIsSwitchedOff(unittest.TestCase):
    """The default position, asserted against the stylesheets themselves.

    Both files ship in every YouTube tab and apply as they stand. What lets a
    switch turn one off is that every rule is written `html:not([data-ntr-off-…])`,
    and content.js sets that attribute only for a switch someone turned off.

    The polarity is the point, not an accident of spelling. Settings are read
    asynchronously while these stylesheets are already live, so there is a
    window with no attribute set at all; written this way that window renders
    the defaults, and written the other way every page would flash the thing
    it is about to hide.
    """

    def test_every_rule_that_paints_is_gated(self):
        for name, css in (("hide-shorts.css", HIDE), ("calm.css", CALM)):
            for selectors, _ in support.css_rules(css):
                if is_palette_block(selectors):
                    continue
                for selector in selectors.split(","):
                    selector = selector.strip()
                    if not selector:
                        continue
                    with self.subTest(name=name, selector=selector):
                        self.assertRegex(
                            selector, r"^html:not\(\[data-ntr-off-[\w-]+\]\)",
                            "an ungated rule cannot be switched off, and a "
                            "rule gated the other way round flashes on load")

    def test_no_rule_is_gated_the_other_way_round(self):
        # `html[data-ntr-…]` would only apply once the settings had been read,
        # which is the flicker this polarity exists to avoid.
        for name, css in (("hide-shorts.css", HIDE), ("calm.css", CALM)):
            for selectors, _ in support.css_rules(css):
                if is_palette_block(selectors):
                    continue
                with self.subTest(name=name, selectors=selectors):
                    self.assertNotRegex(selectors, r"html\[data-ntr-(?!accent)")

    def test_the_only_ungated_blocks_define_variables_and_nothing_else(self):
        # Palettes are exempt because defining a custom property paints
        # nothing on its own. That exemption is only safe while it stays true.
        for selectors, block in support.css_rules(CALM):
            if not is_palette_block(selectors):
                continue
            for prop, _ in support.declarations(block):
                with self.subTest(selectors=selectors, prop=prop):
                    self.assertTrue(prop.startswith("--"),
                                    f"'{selectors}' is ungated but sets {prop}")

    def test_the_gates_are_exactly_the_ones_the_script_sets(self):
        # A gate in the CSS that content.js never sets is a dead rule; one the
        # script sets with no CSS behind it is a switch that does nothing.
        in_css = set(CSS_GATE_RE.findall(support.strip_comments(HIDE))) | \
            set(CSS_GATE_RE.findall(support.strip_comments(CALM)))
        in_script = set(JS_GATE_RE.findall(SETTINGS))
        self.assertEqual(in_css, in_script)


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
        # The README promises these five places specifically, and the menu
        # offers a switch for each.
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

    def test_every_accent_has_a_block_in_both_themes(self):
        for name in accents():
            for theme in ("dark", "light"):
                with self.subTest(accent=name, theme=theme):
                    self.assertEqual(sorted(accent_palette(theme, name)),
                                     ["--ntr-accent", "--ntr-on-accent"])

    def test_calm_css_offers_no_accent_the_menu_cannot_reach(self):
        found = {ACCENT_SELECTOR_RE.match(sel).group(2)
                 for sel, _ in support.css_rules(CALM)
                 if ACCENT_SELECTOR_RE.match(sel)}
        self.assertEqual(found, set(accents()))

    def test_every_variable_used_is_defined(self):
        used = set(VAR_USE_RE.findall(support.strip_comments(CALM)))
        defined = set(palette(DARK)) | set(accent_palette("dark", accents()[0]))
        self.assertEqual(used - defined, set(),
                         "calm.css uses variables no palette defines")

    def test_every_variable_defined_is_used_or_reserved(self):
        # One slot is held for the surface it names rather than read today. It
        # stays in both palettes, and the contrast tests below hold it to the
        # same bar as the rest, so the first rule that uses it is already
        # known to be legible.
        reserved = {"--ntr-dim"}
        used = set(VAR_USE_RE.findall(support.strip_comments(CALM)))
        defined = set(palette(DARK)) | set(accent_palette("dark", accents()[0]))
        self.assertEqual(defined - used - reserved, set(),
                         "calm.css defines variables nothing reads")

    def test_text_colour_is_only_set_where_the_surface_is(self):
        # 1.3.2: the restyle forced its own text colours regardless of
        # YouTube's theme, so a light-theme YouTube got dark text on dark
        # surfaces. The rule that came out of it: only repaint text where this
        # stylesheet also repaints what sits behind it.
        for selectors, block in support.css_rules(CALM):
            if is_palette_block(selectors):
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
                         "--ntr-text", "--ntr-dim"):
                with self.subTest(theme=theme, name=name):
                    self.assertRegex(colours[name].split()[0], HEX_RE.pattern)
        for name in accents():
            for theme in ("dark", "light"):
                colours = accent_palette(theme, name)
                for key in ("--ntr-accent", "--ntr-on-accent"):
                    with self.subTest(theme=theme, accent=name, name=key):
                        self.assertRegex(colours[key].split()[0], HEX_RE.pattern)

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

    def test_text_on_every_accent(self):
        # Selected chips and the notification badge put text on the accent.
        for name in accents():
            for theme, base in self.each_theme():
                c = accent_palette(theme, name)
                with self.subTest(theme=theme, accent=name):
                    self.assertGreaterEqual(
                        support.contrast_ratio(c["--ntr-on-accent"],
                                               c["--ntr-accent"]), 4.5)

    def test_every_accent_is_visible_against_the_background(self):
        # The scrubber and progress bar are UI, not text: 3:1.
        for name in accents():
            for theme, base in self.each_theme():
                c = accent_palette(theme, name)
                with self.subTest(theme=theme, accent=name):
                    self.assertGreaterEqual(
                        support.contrast_ratio(c["--ntr-accent"],
                                               base["--ntr-bg"]), 3.0)

    def test_no_accent_is_youtube_red(self):
        # The whole point of the restyle.
        for name in accents():
            for theme in ("dark", "light"):
                c = accent_palette(theme, name)
                with self.subTest(theme=theme, accent=name):
                    self.assertNotIn(c["--ntr-accent"].lower(),
                                     ("#ff0000", "#f00", "#cc0000", "#ff0033"))


class TheMenuShowsWhatThePageWillUse(unittest.TestCase):
    """options.css repeats the accent colours, because one stylesheet cannot
    read another's variables. A swatch showing a colour the page does not use
    is a menu that lies about what you are picking."""

    def swatches(self) -> dict[str, set[str]]:
        found: dict[str, set[str]] = {}
        for name, colour in SWATCH_RE.findall(OPTIONS):
            found.setdefault(name, set()).add(colour.lower())
        return found

    def test_there_is_a_swatch_for_every_accent(self):
        self.assertEqual(set(self.swatches()), set(accents()))

    def test_each_swatch_shows_both_of_its_real_colours(self):
        for name, shown in self.swatches().items():
            expected = {accent_palette(theme, name)["--ntr-accent"].lower()
                        for theme in ("dark", "light")}
            with self.subTest(accent=name):
                self.assertEqual(shown, expected)


if __name__ == "__main__":
    unittest.main()
