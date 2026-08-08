<div align="center">

<img src="icons/icon-128.png" width="96" alt="No-Tube-Rot icon">

# No-Tube-Rot

**YouTube, minus the feed that was built to keep you there.**

Lands you on your Subscriptions, deletes every Short, and repaints the interface in calm, muted tones — so nothing on the page is fighting for your next click.

![Manifest V3](https://img.shields.io/badge/manifest-v3-4285F4?logo=googlechrome&logoColor=white)
![Chrome · Edge · Brave · Firefox](https://img.shields.io/badge/browsers-Chrome%20%C2%B7%20Edge%20%C2%B7%20Brave%20%C2%B7%20Firefox-0078D6)
![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![No tracking](https://img.shields.io/badge/tracking-none-brightgreen)
![Size](https://img.shields.io/badge/size-under%2020%20KB-lightgrey)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Stars](https://img.shields.io/github/stars/aerusW/No-Tube-Rot?style=social)

</div>

---

<div align="center">

### The home page → your subscriptions

| Before | After |
| :---: | :---: |
| <img src="docs/before-home.jpg" alt="Vanilla YouTube home: red UI, clickbait grid, filter chips" width="420"> | <img src="docs/after-subscriptions.jpg" alt="No-Tube-Rot: calm subscriptions feed with a trimmed sidebar" width="420"> |

### A watch page → just the video

| Before | After |
| :---: | :---: |
| <img src="docs/before-watch.jpg" alt="Vanilla watch page: recommendation rail, red UI" width="420"> | <img src="docs/after-watch.jpg" alt="No-Tube-Rot watch page: full-width video, calm UI, no rail" width="420"> |

</div>

---

## Contents

[Why](#why) · [What it does](#what-it-does) · [Install](#install) · [Usage](#usage) · [Privacy](#privacy) · [Under the hood](#under-the-hood) · [Contributing](#contributing) · [License](#license)

---

## Why

You open YouTube to watch one video from a channel you chose. Forty minutes
later you're three Shorts deep into something you'd never have searched for.

That isn't a discipline problem — it's the interface working as designed. The
home grid is an algorithmic feed, Shorts is an infinite swipe surface, and the
red accents exist to pull your eye. No-Tube-Rot removes those three levers and
leaves the rest of YouTube alone.

**No popups. No settings. No account. No tracking.** Load it once and forget
it's there.

## What it does

* **Opens on your subscriptions, not the algorithm.** `youtube.com` takes you
  straight to your Subscriptions feed — the channels you actually picked.
* **No Shorts, anywhere.** Gone from the home and subscription feeds, the
  sidebar, channel pages, search results, and grids.
* **Shorts open as normal videos.** Click a Short from anywhere and it plays
  in the regular player — scrubber, playback speed, description, and no vertical
  swipe-feed.
* **A calmer interface.** YouTube's alarm-red is swapped for a single muted
  sage accent, surfaces are flat solid colours, and loud buttons are quieted
  down. Works in both YouTube themes — it follows your light/dark setting,
  including "Use device theme".
* **A focused sidebar.** Trimmed to Home, Subscriptions and You — no Explore,
  no "More from YouTube", no promos.
* **Watch pages without the noise.** The recommended "up next" column is
  removed and the video widens to fill the space.

## Install

### Chrome · Edge · Brave · any Chromium browser

1. **Download** this repo ([ZIP](https://github.com/aerusW/No-Tube-Rot/archive/refs/heads/main.zip))
   or clone it, into a folder you'll keep — the browser loads it from there.
   ```bash
   git clone https://github.com/aerusW/No-Tube-Rot.git
   ```
2. Open **`chrome://extensions`** (or `edge://extensions`, `brave://extensions`).
3. Turn on **Developer mode** (top-right).
4. Click **Load unpacked** and select the `No-Tube-Rot` folder.
5. Open YouTube. You'll land on your Subscriptions.

> Prefer a fixed version over the moving `main` branch? Every release ships a
> `.zip` on the [releases page](https://github.com/aerusW/No-Tube-Rot/releases) —
> unzip it and load that folder instead.

> Store listings aren't published yet. Loading unpacked is the supported route
> for now, and it means you can read every line of what you're installing.

### Firefox · Zen

1. Download **`no-tube-rot-<version>.xpi`** from the
   [latest release](https://github.com/aerusW/No-Tube-Rot/releases/latest).
2. Open Firefox and drag the `.xpi` onto the window — or use
   **☰ → Add-ons and themes → ⚙ → Install Add-on From File…**
3. Confirm the install prompt.
4. Open YouTube. You'll land on your Subscriptions.

The `.xpi` is signed by Mozilla, so it installs permanently and survives
restarts. It's distributed here rather than through addons.mozilla.org, which
has one consequence worth knowing:

> **Firefox installs don't update themselves.** To move to a newer version,
> download the new `.xpi` and install it over the top. Watch the
> [releases page](https://github.com/aerusW/No-Tube-Rot/releases) — YouTube
> changes its markup often, and an out-of-date copy shows up as Shorts quietly
> reappearing.

**From source instead:** open `about:debugging#/runtime/this-firefox` →
**Load Temporary Add-on…** → pick `manifest.json` in the repo folder. This is
the development route; a temporary add-on is gone on the next restart. If you
have also loaded the same folder in Chrome, see the
[note below](#a-note-for-anyone-using-both-browsers).

### A note for anyone using both browsers

Loading the repo folder in Chrome makes it write a `_metadata/` directory
inside. Firefox rejects any extension containing reserved underscore-prefixed
names, so **that folder will no longer load in Firefox** until you delete
`_metadata/`. Use separate folders per browser, or install from the release
artifacts above, which never contain it.

## Usage

There's nothing to configure. Once it's installed, just use YouTube normally:

| You do this | You get |
|---|---|
| Go to `youtube.com` | Your **Subscriptions** feed |
| Open any Short | The **normal player**, with full controls |
| Search for anything | Results with **no Shorts shelf** |
| Open a video | A **full-width player**, no up-next rail |

To pause it, disable the extension on your browser's extensions page. To remove
it, delete it from that list.

## Privacy

The extension makes **no network requests of its own**, stores nothing, and has
no analytics, no account, and no remote configuration. Everything happens
locally in your browser, on `www.youtube.com` and nowhere else.

| Permission | Why it's needed |
|---|---|
| `declarativeNetRequest` | Redirect the homepage and Shorts URLs on a hard load, before the page paints. Rules are static and shipped in the repo — they can't be changed remotely. |
| Host access to `www.youtube.com` | Apply the stylesheets and the SPA-navigation redirect. Nothing runs on any other site. |

There is no background service worker and no `storage` permission. If a future
change needed either, it would be called out in the [changelog](CHANGELOG.md).

## Under the hood

Four small files, no build step, no dependencies — under 20 KB in total.

| File | Role |
|------|------|
| `rules.json` | `declarativeNetRequest` rules that redirect the homepage and Shorts URLs on a hard load, before the page paints. |
| `content.js` | Catches YouTube's in-app (SPA) navigations that the network rules can't see, and redirects those too. The two are intentionally redundant so redirects hold whether you type a URL or click through the app. |
| `hide-shorts.css` | Hides every Shorts surface. Matching is locale-independent — YouTube keeps "Shorts" as an untranslated brand name in every language. |
| `calm.css` | The calmer look: one muted accent in place of red, flat surfaces, quieter buttons, a trimmed sidebar, and the recommended-column removal. Has a light and a dark palette, picked from YouTube's own theme setting. Sidebar sections are matched by their link targets, so the trim survives UI-language changes. |

YouTube reshapes its DOM constantly, so selectors are matched on stable hooks —
`href` endpoints and attributes — rather than translated text, and anything
fragile carries a comment explaining what forced it. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the full conventions.

## Contributing

Contributions are very welcome — especially reports that a selector has stopped
matching, since YouTube breaks them regularly. See
**[CONTRIBUTING.md](CONTRIBUTING.md)** for the dev loop, the manual test
surfaces, and how to open a pull request. Please also read our
**[Code of Conduct](CODE_OF_CONDUCT.md)**.

* [Report a bug](../../issues/new?template=bug_report.yml)
* [Request a feature](../../issues/new?template=feature_request.yml)
* [Changelog](CHANGELOG.md)

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE)
file for details.

By contributing, you agree that your contributions will be licensed under the
MIT license.

---

<div align="center">
<sub>Not affiliated with YouTube or Google. If this gave you your attention back, a ⭐ helps others find it.</sub>
</div>
