/*
 * The settings schema, shared by the content script and the menu.
 *
 * Everything that can be turned on lives here once. content.js reads this to
 * decide what to apply, options.js reads it to decide what to draw, and the
 * test suite reads it to check the two can never disagree — a setting that
 * exists in one place and not the other is the failure mode this file is
 * shaped to prevent.
 *
 * Loaded as a plain script in both worlds (first in the content_scripts list,
 * and via a <script> tag in options.html), so it hangs one object off
 * globalThis rather than exporting. Content scripts have no module loader.
 */
'use strict';

globalThis.NTR = (() => {
  // Firefox exposes promise-returning APIs on `browser`, Chromium on `chrome`.
  const api = globalThis.browser ?? globalThis.chrome;

  /*
   * Every setting, and its default.
   *
   * All false. That is the whole point of the 2.0 rewrite: a fresh install
   * changes nothing about YouTube until someone opens the menu and asks it
   * to. `accent` is the one non-boolean, and it only decides *which* colour
   * the recolouring uses once recolouring is switched on.
   */
  const DEFAULTS = {
    // Redirects — handled by declarativeNetRequest on hard loads and by
    // content.js on YouTube's in-app navigations.
    redirectHome: false,
    redirectShortsFeed: false,
    shortsAsVideo: false,

    // Shorts — pure CSS, one switch per surface.
    hideShortsShelves: false,
    hideShortsSearch: false,
    hideShortsItems: false,
    hideShortsSidebar: false,
    hideShortsTab: false,

    // Appearance — pure CSS.
    calmSurfaces: false,
    recolourAccent: false,
    quietButtons: false,
    trimSidebar: false,
    hideUpNext: false,

    // Picture-in-picture — pops the playing video out when you look away.
    // Chromium only; see the note in content.js for what the browser will and
    // will not let an extension do here.
    autoPip: false,
    autoPipOnBlur: false,
    autoPipReturn: false,

    accent: 'sage',
  };

  /*
   * Redirect settings map to static declarativeNetRequest rulesets, which are
   * registered disabled in the manifest and switched on with
   * updateEnabledRulesets. Static rules are the reason a redirect can happen
   * before the homepage is ever requested; a rule built at runtime could not.
   */
  const RULESETS = {
    redirectHome: 'redirect-home',
    redirectShortsFeed: 'redirect-shorts-feed',
    shortsAsVideo: 'shorts-as-video',
  };

  /*
   * CSS settings map to an attribute on <html>. The stylesheets ship with
   * every rule already gated behind one of these, so nothing paints until
   * content.js has read the settings and put the attribute there.
   */
  const ATTRIBUTES = {
    hideShortsShelves: 'data-ntr-shorts-shelves',
    hideShortsSearch: 'data-ntr-shorts-search',
    hideShortsItems: 'data-ntr-shorts-items',
    hideShortsSidebar: 'data-ntr-shorts-sidebar',
    hideShortsTab: 'data-ntr-shorts-tab',
    calmSurfaces: 'data-ntr-surfaces',
    recolourAccent: 'data-ntr-recolour',
    quietButtons: 'data-ntr-quiet',
    trimSidebar: 'data-ntr-trim',
    hideUpNext: 'data-ntr-no-upnext',
  };

  /* Accent choices. Every one of these clears WCAG AA against both theme
     backgrounds, in both directions — asserted in tests/test_stylesheets.py,
     so adding one here without adding its palette block fails the suite. */
  const ACCENTS = ['sage', 'slate', 'clay', 'plum'];

  const REDIRECT_TARGET = 'https://www.youtube.com/feed/subscriptions';

  /**
   * Settings as stored, with anything missing or unrecognised replaced by its
   * default. Storage written by an older version — or by hand — must never be
   * able to switch on something this version does not understand.
   */
  function normalise(stored) {
    const out = { ...DEFAULTS };
    for (const [key, fallback] of Object.entries(DEFAULTS)) {
      const value = stored?.[key];
      if (key === 'accent') {
        out[key] = ACCENTS.includes(value) ? value : fallback;
      } else if (typeof value === 'boolean') {
        out[key] = value;
      }
    }
    return out;
  }

  /** Read the whole settings object. Local storage only — nothing syncs. */
  async function read() {
    return normalise(await api.storage.local.get(Object.keys(DEFAULTS)));
  }

  /** Write one or more settings. */
  async function write(patch) {
    await api.storage.local.set(patch);
  }

  return { api, DEFAULTS, RULESETS, ATTRIBUTES, ACCENTS, REDIRECT_TARGET,
           normalise, read, write };
})();
