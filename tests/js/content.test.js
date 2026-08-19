/*
 * content.js — the SPA half of the redirects.
 *
 * rules.json catches URLs the browser loads over the network. It cannot see
 * YouTube's in-app router, so clicking the logo or opening a Short from a
 * feed never touches the network rules at all; content.js is what covers
 * those, and the two have to agree about where a URL ends up.
 *
 * The script is a plain script with no exports, so it is run in a fresh
 * `node:vm` context with a hand-made `location` and `document`. That is the
 * whole test harness — no dependencies, matching the extension itself.
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
const SOURCE = fs.readFileSync(path.join(ROOT, 'content.js'), 'utf8');
const SUBSCRIPTIONS = 'https://www.youtube.com/feed/subscriptions';

/**
 * Load content.js as if the page had just opened at `href`.
 *
 * Returns the fake window, plus `navigate()` to simulate an in-app navigation
 * the way YouTube does: change the URL, then fire yt-navigate-finish.
 */
function open(href) {
  const url = new URL(href);
  const replaced = [];
  const listeners = new Map();

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

  const document = {
    addEventListener(type, handler) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(handler);
    },
  };

  vm.runInNewContext(SOURCE, { location, document });

  return {
    replaced,
    listeners,
    location,
    navigate(to) {
      const next = new URL(to, 'https://www.youtube.com');
      location.pathname = next.pathname;
      location.search = next.search;
      location.href = next.href;
      for (const handler of listeners.get('yt-navigate-finish') || []) handler();
    },
  };
}

/** Where a cold load of `href` ends up, or null if the script left it alone. */
function landsOn(href) {
  const page = open(href);
  return page.replaced.length ? page.replaced[page.replaced.length - 1] : null;
}

test('the homepage goes to the subscriptions feed', () => {
  assert.equal(landsOn('https://www.youtube.com/'), SUBSCRIPTIONS);
});

test('the homepage with a query string still redirects', () => {
  assert.equal(landsOn('https://www.youtube.com/?gl=GB'), SUBSCRIPTIONS);
});

test('the shorts feed goes to the subscriptions feed', () => {
  assert.equal(landsOn('https://www.youtube.com/shorts'), SUBSCRIPTIONS);
  assert.equal(landsOn('https://www.youtube.com/shorts/'), SUBSCRIPTIONS);
});

test('a single short opens in the normal player', () => {
  assert.equal(landsOn('https://www.youtube.com/shorts/dQw4w9WgXcQ'),
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
});

test('short ids keep their dashes and underscores', () => {
  assert.equal(landsOn('https://www.youtube.com/shorts/a-b_c123'),
    'https://www.youtube.com/watch?v=a-b_c123');
});

test('a shared short drops the tracking query rather than carrying it over', () => {
  // /shorts/<id>?feature=share is how the share sheet writes them. The id is
  // read from the pathname, so the query cannot leak into ?v=.
  assert.equal(landsOn('https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share'),
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
});

test('a short with a trailing path segment still resolves to its id', () => {
  assert.equal(landsOn('https://www.youtube.com/shorts/dQw4w9WgXcQ/something'),
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
});

test('the rest of YouTube is left alone', () => {
  for (const href of [
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://www.youtube.com/feed/subscriptions',
    'https://www.youtube.com/feed/history',
    'https://www.youtube.com/results?search_query=cats',
    'https://www.youtube.com/@someone',
    'https://www.youtube.com/@someone/videos',
    'https://www.youtube.com/playlist?list=PL123',
  ]) {
    assert.equal(landsOn(href), null, `${href} should not have been redirected`);
  }
});

test('a path that merely starts with the word shorts is left alone', () => {
  // /shortsomething is a channel handle's problem, not ours.
  assert.equal(landsOn('https://www.youtube.com/shortsomething'), null);
});

test('the redirect target is not itself redirected', () => {
  // The failure a user cannot escape from: landing somewhere that bounces.
  const page = open('https://www.youtube.com/');
  assert.equal(page.replaced.length, 1);
  page.navigate(SUBSCRIPTIONS);
  assert.equal(page.replaced.length, 1, 'the subscriptions feed redirected again');
});

test('it listens for YouTube in-app navigation', () => {
  const page = open('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
  assert.equal((page.listeners.get('yt-navigate-finish') || []).length, 1,
    'yt-navigate-finish is the only signal the network rules cannot see');
});

test('clicking the logo in-app redirects the same way a cold load does', () => {
  const page = open('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
  assert.deepEqual(page.replaced, []);
  page.navigate('/');
  assert.deepEqual(page.replaced, [SUBSCRIPTIONS]);
});

test('opening a short from a feed redirects the same way', () => {
  const page = open('https://www.youtube.com/feed/subscriptions');
  page.navigate('/shorts/dQw4w9WgXcQ');
  assert.deepEqual(page.replaced, ['https://www.youtube.com/watch?v=dQw4w9WgXcQ']);
});

test('repeated in-app navigation keeps working', () => {
  const page = open('https://www.youtube.com/feed/subscriptions');
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
  assert.doesNotMatch(SOURCE, /location\s*\.\s*assign\s*\(/);
  assert.doesNotMatch(SOURCE, /location\s*\.\s*href\s*=/);
  assert.match(SOURCE, /location\.replace\(/);
});

test('it makes no network requests and stores nothing', () => {
  // The privacy claim in the README, asserted against the shipped source.
  for (const forbidden of ['fetch(', 'XMLHttpRequest', 'chrome.storage',
    'browser.storage', 'localStorage', 'sessionStorage', 'eval(']) {
    assert.ok(!SOURCE.includes(forbidden), `content.js should not use ${forbidden}`);
  }
});

test('it needs no extension APIs at all', () => {
  // Nothing here should require chrome.* — that is what keeps the permission
  // list down to declarativeNetRequest.
  assert.doesNotMatch(SOURCE, /\bchrome\s*\./);
  assert.doesNotMatch(SOURCE, /\bbrowser\s*\./);
});
