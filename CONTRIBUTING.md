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

No-Tube-Rot is deliberately small and opinionated:

- **No settings, no options page, no popup.** Installing it *is* the
  configuration. Anything that would need a toggle is usually the wrong shape
  for this project.
- **No network requests, no storage, no analytics.** The extension must keep
  asking for nothing beyond `declarativeNetRequest` and host access to
  `www.youtube.com`.
- **No background service worker.** Static rules plus content scripts cover
  everything so far; adding one needs a strong reason.

Changes that widen the permission set will be scrutinised heavily — the
zero-data promise in the README is the point of the project.

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
`manifest.json` and `rules.json` changes always need the extension reloaded
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

There is no automated suite — verification is manual, on a live YouTube session.
Walk the surfaces your change touches:

| Area | Check |
|---|---|
| Redirects | `youtube.com` typed fresh (hard load) **and** clicking the YouTube logo in-app (SPA). Also `/shorts` and a specific `/shorts/<id>`. |
| Shorts hiding | Home, Subscriptions, search results, a channel page's tabs, the left sidebar and the collapsed mini sidebar. |
| Calm restyle | Both YouTube themes — avatar → **Appearance** → Dark and Light. Check text contrast, not just background colour. |
| Watch page | The recommended column is gone and the player widens; fullscreen and theatre mode still behave. |
| Both engines | Chromium **and** Firefox. They diverge on extension packaging and on `declarativeNetRequest` support, so a change that works in one is not evidence about the other. |

Please say in the PR which browser and which pages you actually checked.

### Automated checks

CI runs on every push and pull request, and you can run exactly the same checks
locally before you push:

```bash
python .github/scripts/checks.py            # everything except the bump rules
python .github/scripts/checks.py --base main   # also check the version bump
```

It verifies that `manifest.json` and `rules.json` parse, that every file the
manifest references exists, that the issue forms are valid YAML, that the
version is three-component and matches the newest `CHANGELOG.md` entry, that a
bump never reuses an already-tagged version, and that no `console.log` or
`debugger` made it into `content.js`.

These are the mistakes that are invisible in review and obvious in hindsight —
the versioning rules above are enforced here rather than left to memory.

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
manifest.json      # MV3 manifest — permissions, content scripts, ruleset registration
rules.json         # declarativeNetRequest rules: redirect on hard loads, before the page paints
content.js         # SPA-navigation redirects, for the in-app router the network rules can't see
hide-shorts.css    # every Shorts surface: shelves, sidebar entries, channel tabs, grid items
calm.css           # the calm restyle: one accent, flat surfaces, trimmed sidebar, no up-next column
icons/             # 16 / 48 / 128 px extension icons
docs/              # before/after screenshots used by the README

.github/scripts/
  checks.py        # the CI gates, runnable locally; also owns referenced_files()
  package.py       # builds dist/staging + the .zip from the manifest's file list
  release_notes.py # pulls one version's section out of CHANGELOG.md
```

`rules.json` and `content.js` are intentionally redundant: the first covers URLs
you type or open cold, the second covers navigations YouTube handles internally.
Changing a redirect usually means changing both.

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
| **MAJOR** | A core behaviour is removed or reversed, or the extension asks for a **new permission**. Anything that would make an existing user re-evaluate whether they still want it installed. | Adding a `storage` permission |
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
   that leave `manifest.json`, `rules.json`, `content.js` and the stylesheets
   untouched ride along at the current version. A deliberate documentation
   *release* is the exception — that takes a PATCH bump and a changelog entry
   saying so.

### Cutting a release

For Chromium users who install by loading this folder unpacked, every change to
a shipped file is effectively released the moment it lands on `main`. Firefox
users install a signed `.xpi`, which only exists once a tag is pushed — so the
tag is a real publishing event, not just a bookmark.

```bash
# 1. version + changelog land in the same commit as the change
#    manifest.json -> "version": "1.3.5"
#    CHANGELOG.md  -> ## 1.3.5 — YYYY-MM-DD, with Added / Changed / Fixed

# 2. after the PR merges, tag the merge point and push
git checkout main && git pull
git tag -a v1.3.5 -m "v1.3.5"
git push origin v1.3.5
```

Pushing the tag is the whole release. `.github/workflows/release.yml` then:

1. checks the tag matches `manifest.json` — a mismatch fails the run;
2. re-runs `checks.py`, so a broken tree never ships;
3. runs `package.py` to build `dist/staging` and the `.zip`;
4. signs `dist/staging` with `web-ext sign --channel=unlisted`, producing a
   Mozilla-signed `.xpi`;
5. creates the GitHub release with notes read from `CHANGELOG.md` and both
   artifacts attached.

You can rehearse steps 3 and 5 locally:

```bash
python .github/scripts/package.py            # -> dist/
python .github/scripts/release_notes.py 1.3.5
```

Signing needs `AMO_JWT_ISSUER` and `AMO_JWT_SECRET` repository secrets, from
[addons.mozilla.org API credentials](https://addons.mozilla.org/en-US/developers/addon/api/key/).
**AMO refuses to sign a version number it has already seen**, so the rule about
never reusing a released version is enforced by Mozilla too, not just by
`checks.py`.

> The signing step puts Node in CI. The contributor loop is unaffected — editing
> a file and reloading the extension is still the whole thing, with no build
> step and no dependencies.

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
3. **Verify it in a real browser** across the surfaces listed above.
4. **Bump `version` in `manifest.json`** and add a **`CHANGELOG.md`** entry when
   the change is user-visible.
5. **Update the docs** (`README.md`, and the screenshots in `docs/` if the look
   changed) where relevant.
6. **Push** and open a pull request. Fill in the PR template and link any
   related issue.

### Code standards

- Match the style of the surrounding code — comment density, naming, and idiom.
- Comment the *why*, not the *what*. A selector that reads as arbitrary needs a
  note explaining what forced it.
- Group CSS by intent under a `/* ---- Section ---- */` heading, as the existing
  files do.
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
