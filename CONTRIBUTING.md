# Contributing to No-Tube-Rot

Thanks for taking the time to contribute! 🎉 Bug reports, feature ideas,
documentation fixes, and pull requests are all welcome.

This document explains how to set up a development environment and get a change
merged. By participating you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

---

## Ways to contribute

- 🐛 **Report a bug** — open a [bug report](../../issues/new?template=bug_report.yml).
- 💡 **Request a feature** — open a [feature request](../../issues/new?template=feature_request.yml).
- 📖 **Improve the docs** — typos, clarifications, and screenshots are always useful.
- 🔧 **Send a pull request** — see the workflow below.

YouTube ships DOM changes constantly, so the single most valuable contribution
is a report that a selector has stopped matching — ideally with the element's
current markup copied out of DevTools.

---

## What this project is (and isn't)

No-Tube-Rot is deliberately small, and since 2.0 it is deliberately *unopinionated
by default*:

- **Nothing applies until someone switches it on.** This is the rule everything
  else follows from. A new behaviour ships off, behind its own switch, and a
  pull request that turns something on for existing users needs a much better
  argument than "most people want this". Before 2.0 the project shipped its
  opinions and the README called that a feature; the reason it changed is in
  [the README](README.md#why-nothing-is-on-by-default) and worth reading before
  proposing anything that widens the defaults.
- **One switch, one behaviour.** If two things can reasonably be wanted apart,
  they are two switches. "Hide Shorts" is five, because wanting them out of
  search results is not the same as wanting the sidebar entry gone.
- **No network requests, no analytics, no remote configuration.** The extension
  asks for nothing beyond `declarativeNetRequest`, `storage` and host access to
  `www.youtube.com`, and `storage` holds settings and nothing else — local
  only, never `storage.sync`.
- **No background service worker.** Still true after 2.0: the menu switches the
  rulesets itself. Adding one needs a strong reason.

Changes that widen the permission set will be scrutinised heavily — the
zero-data promise in the README is the point of the project. `storage` arrived
in 2.0 and cost a MAJOR version; the next one should cost the same.

### Adding a setting

Four places have to know about it, and the test suite fails if they disagree:

1. **`settings.js`** — add it to `DEFAULTS` (off), and to `RULESETS` if it
   drives a redirect or `ATTRIBUTES` if it gates CSS. Never both.
2. **`options.html`** — add a control whose `id` is the settings key. The menu
   binds by id; don't name the key in `options.js`.
3. **The thing it switches** — a new file under `rules/`, registered disabled in
   the manifest, or a gated rule group in one of the stylesheets.
4. **`README.md`** — a row in the relevant table under *What it can do*.

Nothing else is needed: `content.js` and `options.js` both read the schema, so
neither has to be edited to add a switch.

---

## Development setup

There is no build step, no bundler, and no dependencies. Editing a file and
reloading the extension is the whole loop.

```bash
git clone https://github.com/aerusW/No-Tube-Rot.git
cd No-Tube-Rot
```

**Load it in Chrome / Edge / Brave:**

1. Open `chrome://extensions` (or `edge://extensions`, etc.).
2. Turn on **Developer mode** (top-right).
3. Click **Load unpacked** and select the repository folder.

**Load it in Firefox / Zen:**

1. Open `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on…** and select `manifest.json` in the folder.

A temporary add-on is gone on the next restart — that's fine for development.
Permanent installs come from the signed `.xpi` a release produces.

**After each edit:** press the ↻ reload button on the extension card (Firefox:
**Reload** on the add-on in `about:debugging`), then hard-reload the YouTube tab
(`Ctrl`/`Cmd` + `Shift` + `R`). CSS changes usually show up on a plain reload;
`manifest.json` and the files under `rules/` always need the extension reloaded
first.

> ### ⚠️ Don't load the same folder in both browsers
>
> Loading the folder as an unpacked extension makes Chrome create a
> `_metadata/` directory inside it. It's gitignored and harmless to Chrome —
> but Firefox **rejects any extension containing reserved underscore-prefixed
> names**, so that folder will silently stop loading in Firefox until you
> delete `_metadata/`.
>
> This cost the project a wrongly-open bug for months
> ([#1](https://github.com/aerusW/No-Tube-Rot/issues/1)): the extension was
> fine, the folder wasn't. Keep a separate clone per browser, or `rm -rf
> _metadata/` before switching. Release artifacts are built from an allowlist
> and never contain it.

---

## Testing a change

Two halves, and they cover different things. The automated suite answers
questions that don't need a browser — does this rule redirect the URL it says
it does, do both themes still clear the contrast bar, did a permission appear.
Everything about whether a selector still matches YouTube's current DOM is
manual, because only a browser knows.

### The automated suite

```bash
python tests/run.py          # everything
python tests/run.py -v       # name every test as it runs
python tests/run.py -k shorts   # only tests matching "shorts"
```

No packages to install. The Python tests run on `unittest` and the content
script's tests on Node's built-in runner (`node --test`), so a working Python
and a working Node are the whole setup — and if Node is missing, the
JavaScript half is skipped with a note rather than failing.

```
tests/run.py              the entry point above
tests/support.py          fixtures and helpers; no tests live here
tests/test_rules.py       what each declarativeNetRequest rule does to a URL
tests/test_stylesheets.py gating, palette parity, WCAG contrast, swatch accuracy
tests/test_manifest.py    the permission surface, the menu, the disabled rulesets
tests/test_checks_script.py    checks.py, fed deliberately broken repositories
tests/test_package_script.py   what ends up in a release archive, and what can't
tests/test_release_notes.py    the changelog section a release publishes
tests/js/settings.test.js the schema, and the menu/CSS/ruleset agreeing with it
tests/js/content.test.js  content.js, in a fake DOM under node:vm
```

The two that carry 2.0 are worth knowing by name. `settings.test.js` asserts
every switch defaults to off and that no setting exists without a control, a
gate and something to drive — the wiring nothing checks at runtime.
`test_stylesheets.py` walks both stylesheets and fails on any rule that isn't
behind a gate.

The two redirect suites are worth knowing about together. The rulesets and
`content.js` do the same job on different paths — one on hard loads, one on
YouTube's in-app router — so they are tested against the same URLs, and they
must agree about where each one ends up.

**Adding tests.** A new redirect rule belongs in `test_rules.py` next to the
URLs it should and shouldn't touch; a new palette variable is covered by
`test_stylesheets.py` automatically, contrast included. Selector changes are
the exception — asserting that a string appears in a stylesheet proves nothing
about YouTube's DOM, so those are verified in a browser instead.

### In a browser

Walk the surfaces your change touches:

| Area | Check |
|---|---|
| **A fresh profile** | Install with nothing switched on and confirm YouTube is untouched — no redirect, no hidden shelf, no repaint. This is the one that matters most, and it is the one nobody thinks to do. |
| The menu | Opens from both the toolbar icon and the browser's options screen. Switches persist across a reload; fine-tunes grey out when their parent is off. |
| Redirects | With each switch on: `youtube.com` typed fresh (hard load) **and** clicking the YouTube logo in-app (SPA). Also `/shorts` and a specific `/shorts/<id>`. Then switch it off and confirm the redirect stops. |
| Shorts hiding | Home, Subscriptions, search results, a channel page's tabs, the left sidebar and the collapsed mini sidebar — one switch at a time. |
| Calm restyle | Both YouTube themes — avatar → **Appearance** → Dark and Light — and all four accents. Check text contrast, not just background colour. |
| Watch page | The recommended column is gone and the player widens; fullscreen and theatre mode still behave. |
| Picture-in-picture | Switch tabs, and minimise the window, with a video playing. Then the two fine-tunes. Chromium only — confirm the menu says so on Firefox. |
| Applying live | Toggle a switch with a YouTube tab already open: CSS switches apply immediately, redirects only on the next navigation. |
| Both engines | Chromium **and** Firefox. They diverge on extension packaging, on `declarativeNetRequest` support and on picture-in-picture, so a change that works in one is not evidence about the other. |

Please say in the PR which browser and which pages you actually checked.

### Repository checks

Separate from the tests, and about the repository rather than the extension:

```bash
python .github/scripts/checks.py            # everything except the bump rules
python .github/scripts/checks.py --base main   # also check the version bump
```

It verifies that `manifest.json` and every ruleset it registers parse, that
every file the manifest references exists — following `options.html` into the
assets it loads — that no ruleset is registered enabled, that the issue forms are valid YAML, that the
version is three-component and matches the newest `CHANGELOG.md` entry, that a
bump never reuses an already-tagged version, and that no `console.log` or
`debugger` made it into any shipped script.

It also looks for underscore-prefixed names anywhere in the tree, because one
`_metadata/` is enough to stop the whole folder loading in Firefox. An ignored
one — Chrome's `_metadata/`, a stray `__pycache__/` — is a **warning**, since
loading this folder in Chrome is a supported thing to do and generated files
can't reach a release. It still means Firefox won't touch the folder until you
delete it. A committed one is a failure.

These are the mistakes that are invisible in review and obvious in hindsight —
the versioning rules above are enforced here rather than left to memory.

### What CI runs

Every push and pull request runs three jobs, all of which you can run yourself:

| Job | Command |
|---|---|
| Manifest, changelog and versioning | `python .github/scripts/checks.py --base main` |
| Test suite | `python tests/run.py` |
| Release scripts run on this tree | `python .github/scripts/package.py` and `release_notes.py <version>` |

The third exists because the packaging and release-notes scripts otherwise
only run when a tag is pushed — the one moment they cannot be fixed and retried
under the same version. It builds the archive on every push and attaches it to
the run, so `dist/no-tube-rot-<version>.zip` from any commit is a download away.

A tag runs all of it again before signing anything.

### Writing selectors that survive

YouTube renames custom elements and reshuffles attributes often. Two rules keep
this repo from breaking every few weeks:

- **Match on stable hooks** — `href` endpoints, `is-shorts`, tag names — not on
  translated visible text. The sidebar trim matches link targets precisely so it
  survives a UI-language change.
- **`"Shorts"` is the one safe word.** YouTube leaves it untranslated in every
  locale, so matching it is locale-independent. Match it case-insensitively and
  as a prefix (`^="Short" i`), because YouTube switches between singular and
  plural.

If you must match something fragile, add a comment saying *why* there was no
better hook — the existing files do this throughout, and it's what makes them
repairable later.

---

## Project layout

```
manifest.json      # MV3 manifest — permissions, content scripts, ruleset registration, the menu
settings.js        # the schema: every setting, its default, and what it drives
content.js         # CSS gates, SPA-navigation redirects, picture-in-picture
rules/*.json       # one declarativeNetRequest ruleset per redirect, all registered disabled
hide-shorts.css    # every Shorts surface: shelves, sidebar entries, channel tabs, grid items
calm.css           # palettes, accents, flat surfaces, quiet buttons, sidebar trim, up-next removal
options.html       # the menu — used as both the toolbar popup and the options page
options.css        # the menu's styling
options.js         # the menu's behaviour; also the only place rulesets are switched
icons/             # 16 / 48 / 128 px extension icons
docs/              # before/after screenshots used by the README

tests/             # the automated suite — nothing here ships
.github/scripts/
  checks.py        # the CI gates, runnable locally; also owns referenced_files()
  package.py       # builds dist/staging + the .zip from the manifest's file list
  release_notes.py # pulls one version's section out of CHANGELOG.md
```

`rules/` and `content.js` are intentionally redundant: the first covers URLs you
type or open cold, the second covers navigations YouTube handles internally.
Changing a redirect usually means changing both.

**How "off" stays off**, in two mechanisms:

- **CSS** — both stylesheets load in every YouTube tab, so every rule in them is
  written behind an `html[data-ntr-…]` attribute selector that `content.js` only
  sets for a switch that is on. An ungated rule applies to someone who turned
  nothing on, and `test_stylesheets.py` fails on one.
- **Redirects** — each ruleset is registered `"enabled": false` in the manifest
  and switched on by `options.js`. `checks.py` fails any tree that commits one
  enabled.

---

## Versioning and releases

The `version` field in `manifest.json` is the single source of truth. Git tags,
GitHub releases and `CHANGELOG.md` all follow it.

### The format

Always **three components**, `MAJOR.MINOR.PATCH` — never `1.2`, always `1.2.0`.
Chrome accepts one to four components, which is exactly why the scheme has to be
pinned by convention: a mix of `1.2` and `1.2.1` sorts unpredictably for humans
and reads as an accident.

| Bump | When | Example |
|---|---|---|
| **MAJOR** | A core behaviour is removed or reversed, or the extension asks for a **new permission**. Anything that would make an existing user re-evaluate whether they still want it installed. | 2.0.0: adding `storage`, and making every behaviour opt-in |
| **MINOR** | New user-visible behaviour — another surface hidden, another URL redirected, a new part of the restyle. | Removing the watch-page up-next column |
| **PATCH** | Repairing behaviour that was supposed to work already, with nothing new added. Also used for repository/documentation-only releases, which must say "no functional changes" in the changelog. | A selector YouTube broke |

**Selector rot is a PATCH, not a MINOR.** When YouTube renames an element and a
rule stops matching, restoring it returns promised behaviour — it doesn't add
any. This is the most common change in this repo, so getting it consistently
right matters more than any other rule here.

### The three rules

1. **Bump in the same commit as the change.** Never a standalone "bump version"
   commit. The version a commit carries must be the version that commit ships;
   a separate bump means every commit in between claims a version it isn't.
2. **Never ship a user-visible change under an already-released version.** If
   `1.2.0` is tagged, the next behaviour change is `1.2.1` or `1.3.0` — not more
   commits wearing `1.2.0`.
3. **Docs-only commits don't bump.** README, CONTRIBUTING and screenshot changes
   that leave `manifest.json`, `settings.js`, `rules/`, `content.js`, the
   stylesheets and the menu untouched ride along at the current version. A deliberate documentation
   *release* is the exception — that takes a PATCH bump and a changelog entry
   saying so.

### Cutting a release

For Chromium users who install by loading this folder unpacked, every change to
a shipped file is effectively released the moment it lands on `main`. Firefox
users install a signed `.xpi`, which only exists once a tag is pushed — so the
tag is a real publishing event, not just a bookmark.

```bash
# 1. version + changelog land in the same commit as the change
#    manifest.json -> "version": "1.3.6"
#    CHANGELOG.md  -> ## 1.3.6 — YYYY-MM-DD, with Added / Changed / Fixed

# 2. after the PR merges, tag the merge point and push
git checkout main && git pull
git tag -a v1.3.6 -m "v1.3.6"
git push origin v1.3.6
```

Pushing the tag is the whole release. `.github/workflows/release.yml` then:

1. checks the tag matches `manifest.json` — a mismatch fails the run;
2. re-runs `checks.py` and the test suite, so a broken tree never ships;
3. runs `package.py` to build `dist/staging` and the `.zip`;
4. signs `dist/staging` with `web-ext sign --channel=unlisted`, producing a
   Mozilla-signed `.xpi`;
5. creates the GitHub release with notes read from `CHANGELOG.md` and both
   artifacts attached.

Everything except the signing runs on every push too, so a tag should be
confirming what CI already said rather than finding out. You can rehearse it
locally:

```bash
python tests/run.py
python .github/scripts/checks.py
python .github/scripts/package.py            # -> dist/
python .github/scripts/release_notes.py 1.3.6
```

Signing needs `AMO_JWT_ISSUER` and `AMO_JWT_SECRET` repository secrets, from
[addons.mozilla.org API credentials](https://addons.mozilla.org/en-US/developers/addon/api/key/).
**AMO refuses to sign a version number it has already seen**, so the rule about
never reusing a released version is enforced by Mozilla too, not just by
`checks.py`.

> Node is in CI twice over — `web-ext` signs the `.xpi`, and `node --test` runs
> the content script's tests. Neither reaches the extension: nothing is bundled,
> minified or generated, and the files in a release are byte-for-byte the files
> in the repository. Editing one and reloading the extension is still the whole
> contributor loop.

Tag names are the manifest version prefixed with `v`, and **a tag never moves
once it is pushed.** Checking out `v1.3.2` must always give the exact tree that
shipped as 1.3.2, forever — so if you tagged too early, cut the next patch
version rather than re-pointing the tag.

Docs-only commits landing after a tag simply ride at the current version until
the next bump. They are not part of the tagged release, and that is fine.

### Changelog entries

`CHANGELOG.md` is newest-first, one `## MAJOR.MINOR.PATCH — YYYY-MM-DD` heading
per version, grouped under `### Added`, `### Changed`, `### Fixed` and
`### Documentation` as needed. Write for someone deciding whether to update:
lead with what they'll notice, then why it changed. Entries describe behaviour,
not selectors.

---

## Pull request workflow

1. **Fork** the repository and create a branch off `main`:
   ```bash
   git checkout -b feat/short-description
   ```
2. **Make your change.** Keep commits focused; write a clear, imperative commit
   subject (e.g. `Hide the Shorts shelf in search results`).
3. **Run `python tests/run.py`** and add tests for anything a browser isn't
   needed to judge — a redirect rule, a palette colour, the permission list.
4. **Verify it in a real browser** across the surfaces listed above.
5. **Bump `version` in `manifest.json`** and add a **`CHANGELOG.md`** entry when
   the change is user-visible.
6. **Update the docs** (`README.md`, and the screenshots in `docs/` if the look
   changed) where relevant.
7. **Push** and open a pull request. Fill in the PR template and link any
   related issue.

### Code standards

- Match the style of the surrounding code — comment density, naming, and idiom.
- Comment the *why*, not the *what*. A selector that reads as arbitrary needs a
  note explaining what forced it.
- Group CSS by intent under a `/* ---- Section ---- */` heading, as the existing
  files do.
- **Every CSS rule that paints starts with `html[data-ntr-…]`.** The only
  exemption is a block that defines custom properties and nothing else, because
  defining one paints nothing. The tests enforce both halves of that.
- Keep `!important` scoped to what actually needs to beat YouTube's own styles.
- Prefer hiding a container over hiding its children — leftover headers and
  "Show more" buttons stranded in a gap are a bug in their own right.
- Don't introduce dependencies, build steps, or new permissions without
  discussing it first.

---

## Reporting security issues

Please **do not** open a public issue for security-sensitive problems.

Use GitHub's private reporting instead — **Security → Report a vulnerability**
on [the repository](https://github.com/aerusW/No-Tube-Rot/security/advisories/new).
It's private to you and the maintainer, and keeps the report attached to the
project.

If you'd rather not use GitHub, email francesco.serangeli@proton.me.

Worth knowing what the attack surface actually is: the extension makes no
network requests, stores nothing, and runs only on `www.youtube.com`. The
plausible concerns are the `declarativeNetRequest` redirect rules and anything
that would widen the permission set — see
[what this project is](#what-this-project-is-and-isnt).
