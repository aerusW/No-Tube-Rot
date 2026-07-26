# No-Tube-Rot

**Turn YouTube back into a tool for watching the creators you chose — not an infinite feed built to keep you scrolling.**

No-Tube-Rot drops you straight onto your Subscriptions, removes every Short, and repaints the interface in calm, muted tones so nothing on the page is fighting for your next click. No popups, no settings, no account, no tracking — load it once and forget it's there.

**The home page → your subscriptions**

| Before | After |
| :---: | :---: |
| ![Vanilla YouTube home: red UI, clickbait grid, filter chips](docs/before-home.jpg) | ![No-Tube-Rot: calm subscriptions feed with a trimmed sidebar](docs/after-subscriptions.jpg) |

**A watch page → just the video**

| Before | After |
| :---: | :---: |
| ![Vanilla watch page: recommendation rail, red UI](docs/before-watch.jpg) | ![No-Tube-Rot watch page: full-width video, calm UI, no rail](docs/after-watch.jpg) |

## What it does

- **Opens on your subscriptions, not the algorithm.** `youtube.com` takes you straight to your Subscriptions feed — the channels you actually picked.
- **No Shorts, anywhere.** Gone from the home and subscription feeds, the sidebar, channel pages, search results, and grids.
- **Shorts open as normal videos.** Click a Short from anywhere and it plays in the regular player — with a scrubber, playback speed, and description, and no vertical swipe-feed.
- **A calmer interface.** YouTube's alarm-red is swapped for a single muted sage accent, surfaces are flat solid colours, and the loud buttons are quieted down.
- **A focused sidebar.** Trimmed to Home, Subscriptions and You — no Explore, no "More from YouTube", no promos.
- **Watch pages without the noise.** The recommended "up next" column is removed and the video widens to fill the space.

## Usage

There's nothing to configure. Once it's installed, just use YouTube normally:

- Go to `youtube.com` → you land on your **Subscriptions**.
- Open any Short → it plays as a **normal video**.
- Search and watch as usual → **no Shorts** in the results, and a quieter page throughout.

To pause it, disable the extension in your browser's extensions page; to remove it, delete the folder from the list.

## Install

### Chrome / Edge / Brave / Chromium

1. Download or clone this repo to a folder you'll keep.
2. Open `chrome://extensions` (or `edge://extensions`, etc.).
3. Turn on **Developer mode** (top-right).
4. Click **Load unpacked** and select the `No-Tube-Rot` folder.

### Firefox / Zen

> ⚠️ Firefox-based browsers don't load the extension yet — tracked in [#8](https://github.com/aerusW/No-Tube-Rot/issues/8). Use a Chromium browser for now.

## Under the hood

Four small files, all running locally — the extension makes no network requests of its own and collects nothing.

<details>
<summary>File-by-file</summary>

| File | Role |
|------|------|
| `rules.json` | `declarativeNetRequest` rules that redirect the homepage and Shorts URLs on a hard load, before the page paints. |
| `content.js` | Catches YouTube's in-app (SPA) navigations that the network rules can't see, and redirects those too. The two are intentionally redundant so redirects hold whether you type a URL or click through the app. |
| `hide-shorts.css` | Hides every Shorts surface. Matching is locale-independent — YouTube keeps "Shorts" as an untranslated brand name in every language. |
| `calm.css` | The calmer look: one muted accent in place of red, flat surfaces, quieter buttons, a trimmed sidebar, and the recommended-column removal. Sidebar sections are matched by their link targets, so the trim survives UI-language changes. |

</details>

**Permissions:** `declarativeNetRequest` plus host access to `www.youtube.com`, used only for the redirects.

## License

See [LICENSE](LICENSE).
