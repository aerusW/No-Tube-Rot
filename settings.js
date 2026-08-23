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
   * All on. A fresh install gives the quietest YouTube the extension knows how
   * to produce, with nothing to configure first — the menu exists to hand
   * pieces of YouTube *back*, not to switch the extension on. `accent` is the
   * one non-boolean, and it only decides which colour the recolouring uses.
   */
  const DEFAULTS = {
    // Redirects — handled by declarativeNetRequest on hard loads and by
    // content.js on YouTube's in-app navigations.
    redirectHome: true,
    redirectShortsFeed: true,
    shortsAsVideo: true,

    // Shorts — pure CSS, one switch per surface.
    hideShortsShelves: true,
    hideShortsSearch: true,
    hideShortsItems: true,
    hideShortsSidebar: true,
    hideShortsTab: true,

    // Appearance — pure CSS.
    calmSurfaces: true,
    recolourAccent: true,
    quietButtons: true,
    trimSidebar: true,
    hideUpNext: true,

    // Picture-in-picture — pops the playing video out when you look away.
    // Chromium only; see the note in content.js for what the browser will and
    // will not let an extension do here.
    autoPip: true,
    autoPipOnBlur: true,
    autoPipReturn: true,

    accent: 'sage',
  };

  /*
   * Redirect settings map to static declarativeNetRequest rulesets, which are
   * registered enabled in the manifest and switched off with
   * updateEnabledRulesets. Static rules are the reason a redirect can happen
   * before the homepage is ever requested; a rule built at runtime could not,
   * and neither could one that had to wait for storage to answer.
   */
  const RULESETS = {
    redirectHome: 'redirect-home',
    redirectShortsFeed: 'redirect-shorts-feed',
    shortsAsVideo: 'shorts-as-video',
  };

  /*
   * CSS settings map to an attribute on <html>, and the sense is deliberately
   * inverted: the attribute marks a setting that is switched **off**, and
   * every rule in the stylesheets is written as `html:not([...])`.
   *
   * That is what makes the defaults free. This script runs at document_start
   * but settings arrive asynchronously, so there is a window in which no
   * attribute is set at all — and with the gates this way round, that window
   * renders exactly like the defaults. Were the attribute to mean "on", every
   * page would paint unstyled and then correct itself, which for hiding rules
   * means Shorts flashing up on every single load.
   *
   * The cost is that someone who switches a rule off may see it apply for the
   * few milliseconds before storage answers. That is the rarer case, and a
   * thing appearing late is a smaller failure than a thing appearing wrongly.
   */
  const ATTRIBUTES = {
    hideShortsShelves: 'data-ntr-off-shorts-shelves',
    hideShortsSearch: 'data-ntr-off-shorts-search',
    hideShortsItems: 'data-ntr-off-shorts-items',
    hideShortsSidebar: 'data-ntr-off-shorts-sidebar',
    hideShortsTab: 'data-ntr-off-shorts-tab',
    calmSurfaces: 'data-ntr-off-surfaces',
    recolourAccent: 'data-ntr-off-recolour',
    quietButtons: 'data-ntr-off-quiet',
    trimSidebar: 'data-ntr-off-trim',
    hideUpNext: 'data-ntr-off-upnext',
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
