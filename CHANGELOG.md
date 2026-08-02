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
