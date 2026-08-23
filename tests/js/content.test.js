/*
 * content.js — everything the extension does inside a YouTube tab.
 *
 * Three jobs to cover, and one of them is new in 2.0 and the reason the rest
 * of this file changed shape: with every switch off by default, the most
 * important assertion here is that a page where nothing is turned on comes
 * out untouched. A redirect that fires anyway, or a hiding attribute set
 * anyway, is the 2.0 promise broken.
 *
 * The scripts are plain scripts with no exports, so settings.js and content.js
 * are run in one fresh `node:vm` context — in that order, the way the manifest
 * loads them — against a hand-made location, document, window and storage.
 * That is the whole test harness; no dependencies, matching the extension.
 *
 * Run:  node --test tests/js        (or: python tests/run.py)
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8');
const SETTINGS_SOURCE = read('settings.js');
const CONTENT_SOURCE = read('content.js');
const SUBSCRIPTIONS = 'https://www.youtube.com/feed/subscriptions';

/** Same constructor object on both sides, so `instanceof` holds inside the vm. */
class HTMLVideoElement {
  constructor(props = {}) {
    this.paused = false;
    this.ended = false;
    this.videoWidth = 640;
    this.disablePictureInPicture = false;
    this.autoPictureInPicture = false;
    this.pipRequests = 0;
    this.refuse = false;
    Object.assign(this, props);
  }

  async requestPictureInPicture() {
    this.pipRequests += 1;
    if (this.refuse) {
      const error = new Error('NotAllowedError');
      error.name = 'NotAllowedError';
      throw error;
    }
    this.doc.pictureInPictureElement = this;
    return {};
  }
}

/** Let every pending promise in the sandbox settle. */
const settle = () => new Promise((resolve) => setImmediate(resolve));

/**
 * Load the extension as if a YouTube tab had just opened at `href`.
 *
 * `stored` is what chrome.storage.local already holds — {} for a fresh
 * install, which is the default and the case that matters most.
 */
function open(href, stored = {}) {
  const url = new URL(href);
  const replaced = [];
  const listeners = new Map();
  const windowListeners = new Map();
  const videos = [];
  const attributes = new Map();
  let changeHandler = null;

  const record = (map) => (type, handler) => {
    if (!map.has(type)) map.set(type, []);
    map.get(type).push(handler);
  };
  const fire = (map, type, event = {}) => {
    for (const handler of map.get(type) || []) handler(event);
  };

  const location = {
    pathname: url.pathname,
    search: url.search,
    href,
    replace(target) {
      replaced.push(target);
      // A real replace() tears the page down; nothing after it runs.
      const next = new URL(target);
      this.pathname = next.pathname;
      this.search = next.search;
      this.href = target;
    },
  };

  const documentElement = {
    setAttribute: (name, value) => attributes.set(name, value),
    removeAttribute: (name) => attributes.delete(name),
    getAttribute: (name) => (attributes.has(name) ? attributes.get(name) : null),
  };

  const document = {
    documentElement,
    visibilityState: 'visible',
    pictureInPictureEnabled: true,
    pictureInPictureElement: null,
    addEventListener: record(listeners),
    querySelectorAll: (selector) => (selector === 'video' ? videos : []),
    async exitPictureInPicture() {
      document.pictureInPictureElement = null;
    },
  };

  const storage = {
    local: {
      async get() { return { ...stored }; },
      async set(patch) { Object.assign(stored, patch); },
    },
    onChanged: { addListener: (handler) => { changeHandler = handler; } },
  };

  const window = { addEventListener: record(windowListeners) };
  const sandbox = {
    location, document, window, HTMLVideoElement,
    chrome: { storage },
    setImmediate, queueMicrotask,
  };
  sandbox.globalThis = sandbox;

  const context = vm.createContext(sandbox);
  // Two files, in manifest order — content.js reads the schema off settings.js.
  vm.runInContext(SETTINGS_SOURCE, context);
  vm.runInContext(CONTENT_SOURCE, context);

  const page = {
    replaced, listeners, location, document, videos, attributes, stored,
    gate: (name) => attributes.has(name),

    /** An in-app navigation, the way YouTube does it. */
    navigate(to) {
      const next = new URL(to, 'https://www.youtube.com');
      location.pathname = next.pathname;
      location.search = next.search;
      location.href = next.href;
      fire(listeners, 'yt-navigate-finish');
    },

    addVideo(props) {
      const video = new HTMLVideoElement(props);
      video.doc = document;
      videos.push(video);
      return video;
    },

    play(video) { fire(listeners, 'play', { target: video }); },

    async hide() {
      document.visibilityState = 'hidden';
      fire(listeners, 'visibilitychange');
      await settle();
    },

    async show() {
      document.visibilityState = 'visible';
      fire(listeners, 'visibilitychange');
      await settle();
    },

    async blur() { fire(windowListeners, 'blur'); await settle(); },
    async focus() { fire(windowListeners, 'focus'); await settle(); },

    /** The menu wrote a setting while this tab was open. */
    async change(patch) {
      const changes = {};
      for (const [key, value] of Object.entries(patch)) changes[key] = { newValue: value };
      Object.assign(stored, patch);
      changeHandler(changes, 'local');
      await settle();
    },
  };
  return page;
}

/** Open a page, let the settings land, and hand it back ready to assert on. */
async function opened(href, stored) {
  const page = open(href, stored);
  await settle();
  return page;
}

/** Where a cold load of `href` ends up, or null if it was left alone. */
async function landsOn(href, stored) {
  const page = await opened(href, stored);
  return page.replaced.length ? page.replaced[page.replaced.length - 1] : null;
}

const ALL_REDIRECTS = {
  redirectHome: true, redirectShortsFeed: true, shortsAsVideo: true,
};

/* ---- The default position ---------------------------------------------- */

test('a fresh install redirects nothing at all', async () => {
  for (const href of [
    'https://www.youtube.com/',
    'https://www.youtube.com/?gl=GB',
    'https://www.youtube.com/shorts',
    'https://www.youtube.com/shorts/',
    'https://www.youtube.com/shorts/dQw4w9WgXcQ',
  ]) {
    assert.equal(await landsOn(href), null,
      `${href} was redirected on a fresh install`);
  }
});

test('a fresh install sets no hiding or restyling attribute', async () => {
  const page = await opened('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
  const set = [...page.attributes.keys()].filter((name) => name !== 'data-ntr-accent');
  assert.deepEqual(set, [],
    'the stylesheets are gated on these, so any of them paints something');
});

test('a fresh install still picks an accent, without applying one', async () => {
  // The attribute selects a palette; the rules that read it are gated
  // separately, so naming a colour here paints nothing.
  const page = await opened('https://www.youtube.com/');
  assert.equal(page.attributes.get('data-ntr-accent'), 'sage');
  assert.equal(page.gate('data-ntr-recolour'), false);
});

/* ---- Redirects ---------------------------------------------------------- */

test('the homepage goes to the subscriptions feed once switched on', async () => {
  assert.equal(await landsOn('https://www.youtube.com/', { redirectHome: true }),
    SUBSCRIPTIONS);
});

test('the homepage with a query string still redirects', async () => {
  assert.equal(await landsOn('https://www.youtube.com/?gl=GB', { redirectHome: true }),
    SUBSCRIPTIONS);
});

test('the shorts feed goes to the subscriptions feed once switched on', async () => {
  const on = { redirectShortsFeed: true };
  assert.equal(await landsOn('https://www.youtube.com/shorts', on), SUBSCRIPTIONS);
  assert.equal(await landsOn('https://www.youtube.com/shorts/', on), SUBSCRIPTIONS);
});

test('a single short opens in the normal player once switched on', async () => {
  assert.equal(
    await landsOn('https://www.youtube.com/shorts/dQw4w9WgXcQ', { shortsAsVideo: true }),
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
});

test('short ids keep their dashes and underscores', async () => {
  assert.equal(
    await landsOn('https://www.youtube.com/shorts/a-b_c123', { shortsAsVideo: true }),
    'https://www.youtube.com/watch?v=a-b_c123');
});

test('a shared short drops the tracking query rather than carrying it over', async () => {
  // /shorts/<id>?feature=share is how the share sheet writes them. The id is
  // read from the pathname, so the query cannot leak into ?v=.
  assert.equal(
    await landsOn('https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share',
      { shortsAsVideo: true }),
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
});

test('a short with a trailing path segment still resolves to its id', async () => {
  assert.equal(
    await landsOn('https://www.youtube.com/shorts/dQw4w9WgXcQ/something',
      { shortsAsVideo: true }),
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
});

test('each redirect switch moves only its own URLs', async () => {
  // The point of three rulesets rather than one: switching on the homepage
  // redirect must not quietly start rewriting Shorts as well.
  assert.equal(await landsOn('https://www.youtube.com/shorts/abc',
    { redirectHome: true }), null);
  assert.equal(await landsOn('https://www.youtube.com/', { shortsAsVideo: true }),
    null);
  assert.equal(await landsOn('https://www.youtube.com/shorts',
    { shortsAsVideo: true }), null);
});

test('the rest of YouTube is left alone even with everything on', async () => {
  for (const href of [
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://www.youtube.com/feed/subscriptions',
    'https://www.youtube.com/feed/history',
    'https://www.youtube.com/results?search_query=cats',
    'https://www.youtube.com/@someone',
    'https://www.youtube.com/@someone/videos',
    'https://www.youtube.com/playlist?list=PL123',
  ]) {
    assert.equal(await landsOn(href, ALL_REDIRECTS), null,
      `${href} should not have been redirected`);
  }
});

test('a path that merely starts with the word shorts is left alone', async () => {
  // /shortsomething is a channel handle's problem, not ours.
  assert.equal(await landsOn('https://www.youtube.com/shortsomething', ALL_REDIRECTS),
    null);
});

test('the redirect target is not itself redirected', async () => {
  // The failure a user cannot escape from: landing somewhere that bounces.
  const page = await opened('https://www.youtube.com/', ALL_REDIRECTS);
  assert.equal(page.replaced.length, 1);
  page.navigate(SUBSCRIPTIONS);
  assert.equal(page.replaced.length, 1, 'the subscriptions feed redirected again');
});

test('it listens for YouTube in-app navigation', async () => {
  const page = await opened('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
  assert.equal((page.listeners.get('yt-navigate-finish') || []).length, 1,
    'yt-navigate-finish is the only signal the network rules cannot see');
});

test('clicking the logo in-app redirects the same way a cold load does', async () => {
  const page = await opened('https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    { redirectHome: true });
  assert.deepEqual(page.replaced, []);
  page.navigate('/');
  assert.deepEqual(page.replaced, [SUBSCRIPTIONS]);
});

test('in-app navigation is gated too', async () => {
  const page = await opened('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
  page.navigate('/');
  page.navigate('/shorts/abc');
  assert.deepEqual(page.replaced, []);
});

test('an in-app navigation before the settings land does nothing', async () => {
  // The gap between document_start and storage answering. Doing nothing is
  // the only safe answer: acting on defaults we have not read yet would
  // redirect someone who switched the redirect off.
  const page = open('https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    { redirectHome: true });
  page.navigate('/');
  assert.deepEqual(page.replaced, []);
});

test('opening a short from a feed redirects the same way', async () => {
  const page = await opened('https://www.youtube.com/feed/subscriptions',
    { shortsAsVideo: true });
  page.navigate('/shorts/dQw4w9WgXcQ');
  assert.deepEqual(page.replaced, ['https://www.youtube.com/watch?v=dQw4w9WgXcQ']);
});

test('repeated in-app navigation keeps working', async () => {
  const page = await opened('https://www.youtube.com/feed/subscriptions', ALL_REDIRECTS);
  page.navigate('/shorts/aaa');
  page.navigate('/watch?v=bbb');
  page.navigate('/');
  assert.deepEqual(page.replaced, [
    'https://www.youtube.com/watch?v=aaa',
    SUBSCRIPTIONS,
  ]);
});

test('it navigates with replace, not assign', () => {
  // location.assign() would leave the algorithmic homepage in the back stack,
  // so Back would bounce between the two.
  assert.doesNotMatch(CONTENT_SOURCE, /location\s*\.\s*assign\s*\(/);
  assert.doesNotMatch(CONTENT_SOURCE, /location\s*\.\s*href\s*=/);
  assert.match(CONTENT_SOURCE, /location\.replace\(/);
});

/* ---- CSS gates ---------------------------------------------------------- */

test('each switch sets exactly its own attribute', async () => {
  const cases = {
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
  for (const [key, attribute] of Object.entries(cases)) {
    const page = await opened('https://www.youtube.com/feed/subscriptions',
      { [key]: true });
    const set = [...page.attributes.keys()].filter((n) => n !== 'data-ntr-accent');
    assert.deepEqual(set, [attribute], `${key} set ${set} instead of ${attribute}`);
  }
});

test('the redirects set no attribute of their own', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x', ALL_REDIRECTS);
  const set = [...page.attributes.keys()].filter((n) => n !== 'data-ntr-accent');
  assert.deepEqual(set, []);
});

test('a chosen accent reaches the page', async () => {
  const page = await opened('https://www.youtube.com/',
    { recolourAccent: true, accent: 'plum' });
  assert.equal(page.attributes.get('data-ntr-accent'), 'plum');
});

test('an accent the extension does not ship falls back to the default', async () => {
  // Storage is writable by hand and by older versions; an unknown value must
  // not leave the page with a palette that defines nothing.
  const page = await opened('https://www.youtube.com/', { accent: 'neon' });
  assert.equal(page.attributes.get('data-ntr-accent'), 'sage');
});

test('changing a setting repaints an open tab without a reload', async () => {
  const page = await opened('https://www.youtube.com/feed/subscriptions');
  assert.equal(page.gate('data-ntr-shorts-items'), false);
  await page.change({ hideShortsItems: true });
  assert.equal(page.gate('data-ntr-shorts-items'), true);
  await page.change({ hideShortsItems: false });
  assert.equal(page.gate('data-ntr-shorts-items'), false);
});

test('switching a redirect on does not move the page you are already on', async () => {
  // Redirects act on a navigation. Moving the tab out from under someone who
  // just opened the menu would be a surprise, not a feature.
  const page = await opened('https://www.youtube.com/');
  await page.change({ redirectHome: true });
  assert.deepEqual(page.replaced, []);
});

/* ---- Picture-in-picture ------------------------------------------------- */

test('hiding the page does nothing when picture-in-picture is off', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x');
  const video = page.addVideo();
  await page.hide();
  assert.equal(video.pipRequests, 0);
});

test('hiding the page pops the playing video out once switched on', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x', { autoPip: true });
  const video = page.addVideo();
  await page.hide();
  assert.equal(video.pipRequests, 1);
  assert.equal(page.document.pictureInPictureElement, video);
});

test('a paused or finished video is left where it is', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x', { autoPip: true });
  const paused = page.addVideo({ paused: true });
  const ended = page.addVideo({ ended: true });
  await page.hide();
  assert.equal(paused.pipRequests, 0);
  assert.equal(ended.pipRequests, 0);
});

test('a video that forbids picture-in-picture is respected', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x', { autoPip: true });
  const video = page.addVideo({ disablePictureInPicture: true });
  await page.hide();
  assert.equal(video.pipRequests, 0);
});

test('an audio-only element is not popped out', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x', { autoPip: true });
  const video = page.addVideo({ videoWidth: 0 });
  await page.hide();
  assert.equal(video.pipRequests, 0);
});

test('a refused request is swallowed rather than thrown', async () => {
  // Without a user gesture the browser says no, and that is the expected
  // path, not a bug to surface.
  const page = await opened('https://www.youtube.com/watch?v=x', { autoPip: true });
  const video = page.addVideo({ refuse: true });
  await page.hide();
  assert.equal(video.pipRequests, 1);
  assert.equal(page.document.pictureInPictureElement, null);
});

test('a playing video is marked so the browser can hand it off itself', async () => {
  // The attribute is the path that needs no gesture at all.
  const page = await opened('https://www.youtube.com/watch?v=x', { autoPip: true });
  const video = page.addVideo();
  page.play(video);
  assert.equal(video.autoPictureInPicture, true);
});

test('videos are not marked when the switch is off', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x');
  const video = page.addVideo();
  page.play(video);
  assert.equal(video.autoPictureInPicture, false);
});

test('coming back closes a window it opened, when asked to', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x',
    { autoPip: true, autoPipReturn: true });
  page.addVideo();
  await page.hide();
  assert.notEqual(page.document.pictureInPictureElement, null);
  await page.show();
  assert.equal(page.document.pictureInPictureElement, null);
});

test('coming back leaves it open when not asked to', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x', { autoPip: true });
  page.addVideo();
  await page.hide();
  await page.show();
  assert.notEqual(page.document.pictureInPictureElement, null);
});

test('it never closes a picture-in-picture window it did not open', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x',
    { autoPip: true, autoPipReturn: true });
  const video = page.addVideo();
  // The user opened this one with YouTube's own button.
  page.document.pictureInPictureElement = video;
  await page.show();
  assert.equal(page.document.pictureInPictureElement, video);
});

test('an already-floating video is not requested again', async () => {
  const page = await opened('https://www.youtube.com/watch?v=x', { autoPip: true });
  const video = page.addVideo();
  page.document.pictureInPictureElement = video;
  await page.hide();
  assert.equal(video.pipRequests, 0);
});

test('losing focus pops out only when that fine-tune is on', async () => {
  const off = await opened('https://www.youtube.com/watch?v=x', { autoPip: true });
  const quiet = off.addVideo();
  await off.blur();
  assert.equal(quiet.pipRequests, 0);

  const on = await opened('https://www.youtube.com/watch?v=x',
    { autoPip: true, autoPipOnBlur: true });
  const video = on.addVideo();
  await on.blur();
  assert.equal(video.pipRequests, 1);
});

test('the fine-tunes do nothing on their own', async () => {
  // They are drawn under a parent switch; storage can still hold them alone.
  const page = await opened('https://www.youtube.com/watch?v=x',
    { autoPipOnBlur: true, autoPipReturn: true });
  const video = page.addVideo();
  await page.blur();
  await page.hide();
  assert.equal(video.pipRequests, 0);
});

/* ---- The promises the README makes ------------------------------------- */

test('nothing makes a network request or reaches remote storage', async () => {
  for (const source of [CONTENT_SOURCE, SETTINGS_SOURCE]) {
    for (const forbidden of ['fetch(', 'XMLHttpRequest', 'localStorage',
      'sessionStorage', 'eval(', 'storage.sync']) {
      assert.ok(!source.includes(forbidden), `should not use ${forbidden}`);
    }
  }
});

test('settings are stored locally and never synced', async () => {
  assert.match(SETTINGS_SOURCE, /storage\.local/);
  assert.doesNotMatch(SETTINGS_SOURCE, /storage\.sync/);
});

test('the only extension API either script touches is storage', async () => {
  // No tabs, no scripting, no host access beyond the content script's own.
  const body = (CONTENT_SOURCE + SETTINGS_SOURCE).replace(/\/\*[\s\S]*?\*\//g, '');
  for (const forbidden of ['.tabs', '.scripting', '.webRequest', '.cookies',
    '.downloads', '.history', '.bookmarks']) {
    assert.ok(!body.includes(forbidden), `should not use ${forbidden}`);
  }
});
