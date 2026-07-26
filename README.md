# No-Tube-Rot

Get rid of Shorts and the endless YouTube homepage. See the channels you
subscribed to — not endless AI slop.

A tiny, zero-config browser extension that:

- **Redirects the YouTube homepage** (`youtube.com`) straight to your
  **Subscriptions** feed (`youtube.com/feed/subscriptions`).
- **Hides all Shorts** — shelves, the sidebar entry, the channel-page tab, and
  individual Shorts scattered through grids, lists and search results.
- **Calms the look** — replaces YouTube's alarm-red with one muted accent,
  flattens surfaces to solid colours, quiets the buttons, and trims the left
  sidebar down to Home, Subscriptions and You.

No popups, no options, no accounts, no tracking. Install it and forget it.

## How it works

| File | Role |
|------|------|
| `rules.json` | A `declarativeNetRequest` rule that redirects the homepage on a hard load, before the page paints. |
| `content.js` | Catches YouTube's in-app (SPA) navigations back to the homepage that the network rule can't see, and redirects those too. The two are intentionally redundant so the redirect holds whether you type the URL or click the logo. |
| `hide-shorts.css` | A content stylesheet that hides every Shorts surface. Matching is locale-independent: YouTube keeps "Shorts" as an untranslated brand name in every language. |
| `calm.css` | A content stylesheet for the calmer look: one muted sage accent in place of red, flat solid surfaces, quieter buttons, and a trimmed sidebar. Sidebar sections are matched by their link targets, so the trim survives UI-language changes. |

## Install

### Chrome / Edge / Brave / Zen (Chromium)

1. Download or clone this repo to a folder you'll keep.
2. Go to `chrome://extensions` (`edge://extensions`, etc.).
3. Turn on **Developer mode** (top-right).
4. Click **Load unpacked** and select the `No-Tube-Rot` folder.

### Firefox / Zen (Firefox-based)

Temporary install (cleared when the browser restarts):

1. Go to `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on…**.
3. Select the `manifest.json` file inside the `No-Tube-Rot` folder.

Firefox 121 or newer is required (the Shorts-hiding CSS relies on the `:has()`
selector, which Firefox enabled by default in 121).

## Permissions

- `declarativeNetRequest` and host access to `www.youtube.com` — used only for
  the homepage redirect. The extension makes no network requests of its own and
  collects nothing.

## License

See [LICENSE](LICENSE).
