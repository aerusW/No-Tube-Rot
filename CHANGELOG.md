# Changelog

All notable changes to this project are documented here. Versions match the
`version` field in `manifest.json` and follow the scheme described in
[CONTRIBUTING.md](CONTRIBUTING.md#versioning-and-releases): three-component
`MAJOR.MINOR.PATCH`, bumped in the same commit as the change it ships.

> **Note on version numbers.** Releases up to and including the calm restyle
> were numbered inconsistently — two-component versions, features that shipped
> under an already-released number, and one standalone "bump" commit. The
> history was renumbered to a single consistent scheme, so the numbers below are
> the canonical ones. Earlier clones may show `1.0`, `1.1`, `1.2`, `1.2.1` and
> `1.2.2` for the same changes.

## 2.0.0 — 2026-08-23

**Everything it does is now a switch — and every switch starts on.**

Nothing about a fresh install changes. Install it, and YouTube is as quiet as
this extension knows how to make it, with no setup and nothing to configure.
What is new is the way *back*: a menu that hands you any single piece of
YouTube without giving up the rest.

Upgrading from 1.x keeps the behaviour you already had, and adds automatic
picture-in-picture on top.

### Added

* **A configuration menu**, reachable from the toolbar icon and from the
  browser's extension options screen — the same page either way. It is styled
  the way the extension styles YouTube: flat surfaces, hairline rules, one
  accent, and no animation beyond the switches themselves.
* **16 individual switches.** Every behaviour the extension has ever had can
  now be turned off on its own. Hiding Shorts is five switches, one per
  surface, because wanting them out of your search results is not the same as
  wanting the sidebar entry gone. The redirects are three, because wanting a
  Short to open in the normal player is no reason to have the address you
  typed replaced. The calm restyle is four, plus the up-next column, which is
  now separate from the rest of the look.
* **Four accents to choose from** — sage, slate, clay and plum — where 1.x had
  one. Each is defined twice, for the light and dark themes, and every one
  clears WCAG AA against its background and for text sitting on it.
* **Automatic picture-in-picture.** A playing video follows you into a
  floating window when the tab or the browser stops being visible, and goes
  back when you return. Two fine-tunes: whether merely losing focus counts,
  and whether coming back closes the window again. It only ever closes a
  window it opened itself. Chromium only — Firefox draws its own
  picture-in-picture control and exposes no API for it, and the menu says so
  there rather than offering switches that quietly do nothing.
* **A "turn everything back on" button**, which returns a copy to the state it
  installs in.

### Changed

* **A new permission: `storage`.** It holds your settings and nothing else, in
  local storage, which does not sync between devices or leave the machine. A
  default install writes nothing at all — storage is only touched once you
  switch something off. This is what makes the release a MAJOR bump under the
  project's own rules.
* **The redirects are one `declarativeNetRequest` ruleset each**, registered
  enabled and switched off from the menu, so turning one off genuinely
  unregisters the rule rather than working around it.
* **The stylesheets are gated rather than unconditional.** Every rule is now
  written `html:not([data-ntr-off-…])`, and the content script sets that
  attribute only for a switch you turned off. The polarity is deliberate:
  settings are read asynchronously while the stylesheets are already live, so
  there is a brief window with no attribute set, and this way round that
  window renders the defaults. Gated the other way, every page load would show
  the Shorts shelves and then snatch them away.

### Project

* **The release archive follows the menu into the files it loads.** The
  allowlist is derived from `manifest.json`, and the manifest names
  `options.html` but has no way to know that page pulls in `options.css` and
  `options.js` — so packaging now reads referenced HTML for its local `href`
  and `src` assets. Without it the release would have shipped a menu that
  opens blank.
* **`checks.py` fails any tree that registers a ruleset disabled**, so the
  default position is enforced rather than remembered. It also parses every
  ruleset the manifest registers rather than a hardcoded filename, and looks
  for debug leftovers in every shipped script rather than only `content.js`.
* **A signing workflow for test builds** (`sign-test.yml`). Pushing
  `sign/<version>` produces a Mozilla-signed `.xpi` without creating a tag or
  a release, so a branch can be tested in Firefox properly. It refuses to sign
  the version in `manifest.json`, since AMO never signs a version twice and
  burning that one would leave the real release unsignable.
* **`release_notes.py` writes UTF-8 explicitly.** A Windows console defaults to
  a legacy code page and crashed on a non-ASCII changelog entry — on the one
  machine CONTRIBUTING tells contributors to rehearse a release from.
* **The test suite covers the new shape**: that a fresh install already
  redirects and sets no off-switch attribute, that switching one thing off
  marks exactly one gate and moves only its own URLs, that every setting has a
  control in the menu and every control is a real setting, that the CSS gates
  are exactly the ones the script sets and none is gated the wrong way round,
  and that the swatch shown for an accent is the colour the page will use.

### Documentation

* The README and CONTRIBUTING no longer describe the project as having no
  settings. Both now explain the default position, what each switch does, and
  why the defaults are the strong ones rather than the safe ones.

## 1.3.6 — 2026-08-17

### Fixed

* **Shorts opened from a share link now play.** A Short reached by a typed or
  pasted URL carrying a query string — `youtube.com/shorts/<id>?feature=share`,
  which is exactly what YouTube's own share sheet produces, or a link with a
  timestamp — redirected to a watch page that could not load. The redirect rule
  matched the URL only as far as the video id, and a `declarativeNetRequest`
  substitution replaces just the part it matched, so the original query string
  stayed on the end: `watch?v=<id>?feature=share`, which YouTube reads as an id
  that doesn't exist. Shorts opened from inside YouTube were never affected,
  and neither were plain `/shorts/<id>` links.

### Project

* **A test suite** (`tests/`), covering the redirect rules and the content
  script — including the bug above, which is the kind that only shows up on a
  URL nobody types by hand — the stylesheet palettes and their contrast, the
  permission surface, and the three release scripts. It runs on Python's
  `unittest` and Node's built-in test runner, so it needs nothing installed:
  `python tests/run.py`.
* **CI runs it on every push and pull request**, alongside the existing
  manifest and versioning checks, and again before anything is published.
* **The release scripts are now exercised on every push** rather than for the
  first time during a release, which is the one moment they cannot be fixed
  and retried under the same version.
* **`checks.py` reports reserved underscore-prefixed names** anywhere in the
  tree — a warning for a generated one, a failure for a committed one. Chrome
  writes `_metadata/` into any folder it loads unpacked and Firefox then
  refuses to load that folder at all: the trap behind
  [#1](https://github.com/aerusW/No-Tube-Rot/issues/1), now visible locally
  instead of arriving as a bug report.

### Documentation

* CONTRIBUTING describes the test suite and how to run it, replacing the note
  that verification was manual only. The manual test table stays: it covers
  what a browser has to answer for, which is most of this project.

## 1.3.5 — 2026-08-08

Packaging and documentation — **no functional changes.** The extension behaves
exactly as it did in 1.3.4, on every browser.

### Fixed

* **Firefox and Zen were never actually broken** ([#1](https://github.com/aerusW/No-Tube-Rot/issues/1)).
  The extension had been reported as failing to load on Firefox-based browsers
  since launch. The cause was not in the extension: loading the repository
  folder in Chrome makes Chrome write a generated `_metadata/` directory into
  it, and Firefox rejects any extension containing reserved
  underscore-prefixed names. Testing both browsers from one folder therefore
  broke Firefox, while a clean checkout works unmodified. No source change was
  needed — `declarativeNetRequest`, the `regexFilter` rules and
  `strict_min_version` were all fine as they stood.

### Added

* **Signed Firefox releases.** Every tag now publishes a Mozilla-signed `.xpi`
  alongside the Chromium `.zip`. Firefox refuses unsigned add-ons, and
  `about:debugging` only ever produced a temporary add-on that vanished on
  restart — so this is the first permanent Firefox install the project has had.
  Distributed from the releases page rather than addons.mozilla.org, which
  means Firefox installs must be updated by hand.
* **A release workflow** (`.github/workflows/release.yml`) that verifies the tag
  matches the manifest, re-runs the checks, packages, signs and publishes.
* **`package.py`**, which builds the release archive from an allowlist derived
  from `manifest.json`. `_metadata/` and anything else untracked cannot end up
  in a package by construction — the bug above cannot recur.
* **`release_notes.py`**, so release bodies are read from `CHANGELOG.md`
  instead of written twice.

### Documentation

* A real **Firefox · Zen install section** in the README, replacing the notice
  saying Firefox was unsupported.
* A prominent **warning in CONTRIBUTING** against loading one folder in both
  browsers — the trap that caused all of this.
* Firefox added to the browser badge, the issue chooser and the bug form; both
  templates no longer describe Firefox as broken.
* Both engines added to the manual test table.

## 1.3.4 — 2026-08-02

Documentation only — **no functional changes.** The extension behaves exactly
as it did in 1.3.3.

### Documentation

* Removed the emoji from the README headings and feature list
  ([#4](https://github.com/aerusW/No-Tube-Rot/pull/4), thanks
  [@GitAlexein](https://github.com/GitAlexein)).
* Fixed the contents menu links, which pointed at the old emoji anchors.

## 1.3.3 — 2026-08-01

Repository, documentation and community polish — **no functional changes.**
The extension behaves exactly as it did in 1.3.2.

### Documentation

* Rewrote the **README** as a product page: badge row, a one-line pitch, the
  before/after screenshots promoted to the top, a "Why" section framing the
  problem, and a contents menu.
* Documented the **privacy position** explicitly — no network requests, no
  storage, no analytics, no account — and listed what each permission is for.
* Added a **CHANGELOG.md** covering the full release history back to 1.0.0.
* Added **CONTRIBUTING.md**, covering the no-build dev loop, how to reload the
  extension, the manual test surfaces to walk, the selector conventions (stable
  hooks over translated text) that keep the CSS from rotting, and a **versioning
  and release policy**.
* Added a Contributor Covenant **CODE_OF_CONDUCT.md**.

### Project

* **Renumbered the version history** to a consistent three-component scheme and
  tagged every release point — the repository previously had no tags and no
  published releases at all.
* Added GitHub **issue forms** — a bug report that collects browser, extension
  version and YouTube theme, and a feature request that states the no-settings
  design constraint up front.
* Added a **pull request template** with an extension-specific test checklist
  (both themes, hard load *and* SPA navigation) and the versioning rules.
* Added an issue **chooser** pointing Firefox users at the existing tracking
  issue and security reports to a private channel.

## 1.3.2 — 2026-07-30

### Fixed

* **Dark-mode titles were hard to read.** The restyle forced its own dark
  palette regardless of YouTube's setting, so a light-theme YouTube got dark
  surfaces with dark text. The palette is now theme-scoped: it follows
  YouTube's own Appearance setting — including "Use device theme" — and never
  overrides YouTube's body text colours.

## 1.3.1 — 2026-07-29

### Fixed

* **The Shorts shelf in search results.** Search shelves carry no
  Shorts-specific tag or attribute, so hiding only the items left the "Shorts"
  header and its "Show more" button stranded between results. The whole shelf
  is now matched by what it holds and hidden as a unit.

## 1.3.0 — 2026-07-26

### Added

* **Watch pages without the up-next column.** The recommended rail is removed
  and the video widens to fill the reclaimed space.

### Documentation

* Rewrote the README as product-first, with usage instructions and before/after
  screenshots of the home and watch pages.

## 1.2.0 — 2026-07-26

### Added

* **Shorts open in the normal player.** A `/shorts/<id>` URL now redirects to
  the standard watch page, so a Short gets a scrubber, playback speed and a
  description instead of the vertical swipe feed. The Shorts feed itself
  redirects to Subscriptions.
* **The calm restyle.** YouTube's alarm-red is replaced by a single muted sage
  accent, surfaces become flat solid colours, loud buttons recede to outlines,
  and the left sidebar is trimmed to Home, Subscriptions and You.

## 1.1.0 — 2026-07-26

### Added

* Extension icons at 16, 48 and 128 px.
* A README.

### Changed

* Raised the Firefox minimum version in `browser_specific_settings`.

## 1.0.1 — 2026-07-26

### Fixed

* Shorts-hiding selectors that YouTube's DOM changes had broken.

## 1.0.0 — 2026-05-25

Initial release.

### Added

* **Homepage redirect** — `youtube.com` lands on your Subscriptions feed
  instead of the algorithmic home grid, via `declarativeNetRequest` on hard
  loads and a content script for YouTube's in-app navigation.
* **Shorts hidden everywhere** — feed shelves, sidebar entries, channel tabs
  and grid items.
* A gecko extension ID, for permanent installation on Firefox.
