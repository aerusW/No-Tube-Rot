/*
 * The page-side half of the extension: whatever is switched on in the menu,
 * applied to a YouTube tab.
 *
 * Three jobs, and they are independent of each other:
 *
 *   1. Put the CSS gates on <html>. Both stylesheets ship with every rule
 *      behind an attribute selector, so nothing they contain paints until the
 *      matching setting has been read and its attribute set here.
 *   2. Redirect YouTube's in-app navigations. declarativeNetRequest catches
 *      URLs the browser loads over the network; it cannot see the SPA router,
 *      so clicking the logo or opening a Short from a feed is this file's
 *      problem. The two are intentionally redundant and must agree.
 *   3. Pop the video out into picture-in-picture when the page stops being
 *      visible.
 *
 * On timing: settings arrive asynchronously, and this script runs at
 * document_start — before YouTube has parsed its own markup, let alone
 * painted. The listeners below are therefore registered synchronously and
 * simply do nothing while `settings` is still null, rather than being
 * registered later and missing an event.
 */
'use strict';

const { api, ATTRIBUTES, REDIRECT_TARGET } = globalThis.NTR;

/** Null until the first read resolves; every handler below tolerates that. */
let settings = null;

/* ---- CSS gates ---------------------------------------------------------- */

function paint() {
  const html = document.documentElement;
  if (!html) return;
  for (const [key, attribute] of Object.entries(ATTRIBUTES)) {
    if (settings[key]) {
      html.setAttribute(attribute, '');
    } else {
      html.removeAttribute(attribute);
    }
  }
  // Always present: it selects a palette rather than applying one, and the
  // rules that read the accent are gated on their own attributes.
  html.setAttribute('data-ntr-accent', settings.accent);
}

/* ---- Redirects ---------------------------------------------------------- */

function redirect() {
  if (!settings) return;
  const path = location.pathname;

  // Homepage -> subscriptions feed.
  if (settings.redirectHome && path === '/') {
    location.replace(REDIRECT_TARGET);
    return;
  }

  // Shorts feed (no video id) -> subscriptions feed.
  if (settings.redirectShortsFeed && (path === '/shorts' || path === '/shorts/')) {
    location.replace(REDIRECT_TARGET);
    return;
  }

  // A specific Short -> the same video in the normal player.
  if (settings.shortsAsVideo) {
    const short = path.match(/^\/shorts\/([\w-]+)/);
    if (short) {
      location.replace('https://www.youtube.com/watch?v=' + short[1]);
      return;
    }
  }
}

/* ---- Picture-in-picture ------------------------------------------------- */
/*
 * What a browser will actually allow here is the whole story.
 *
 * requestPictureInPicture() normally demands a transient user gesture, and
 * "you switched away from the window" is by definition not one. Chromium
 * relaxes that for a video carrying `autoPictureInPicture` — the attribute
 * that exists precisely so a page can hand off to PiP when it is hidden — so
 * the attribute is the mechanism, and the explicit request below is a
 * fallback for the case where the gesture is still warm. The request is
 * expected to be rejected sometimes; a rejection is not an error worth
 * reporting, so it is swallowed.
 *
 * Firefox implements picture-in-picture as a browser control rather than a
 * web API: `document.pictureInPictureEnabled` is absent, nothing below fires,
 * and the setting does nothing. That is checked rather than assumed.
 */

/** True once we put a video into PiP, so we never close one the user opened. */
let pipIsOurs = false;

function pipSupported() {
  return document.pictureInPictureEnabled === true;
}

/** The video worth popping out: playing, on-screen, and allowed to be. */
function playingVideo() {
  for (const video of document.querySelectorAll('video')) {
    if (video.paused || video.ended) continue;
    if (video.disablePictureInPicture) continue;
    if (!video.videoWidth) continue; // audio-only or not yet loaded
    return video;
  }
  return null;
}

/** Mark a video so the browser can hand it off without a gesture. */
function markForAutoPip(video) {
  if (!video) return;
  video.autoPictureInPicture = settings?.autoPip === true;
}

async function enterPip() {
  if (!settings?.autoPip || !pipSupported()) return;
  if (document.pictureInPictureElement) return;
  const video = playingVideo();
  if (!video) return;
  try {
    await video.requestPictureInPicture();
    pipIsOurs = true;
  } catch {
    // No user activation, or the browser declined. The autoPictureInPicture
    // attribute is the path that does not need us at all.
  }
}

async function leavePip() {
  if (!settings?.autoPipReturn || !pipSupported()) return;
  if (!document.pictureInPictureElement || !pipIsOurs) return;
  try {
    await document.exitPictureInPicture();
  } catch {
    // The window was already closed by hand.
  }
  pipIsOurs = false;
}

function onVisibilityChange() {
  if (document.visibilityState === 'hidden') {
    enterPip();
  } else {
    leavePip();
  }
}

function onBlur() {
  if (settings?.autoPipOnBlur) enterPip();
}

function onFocus() {
  if (settings?.autoPipOnBlur) leavePip();
}

/* Catches every video the page starts, including the ones YouTube swaps in on
   an in-app navigation, without polling or a MutationObserver. */
function onPlay(event) {
  if (event.target instanceof HTMLVideoElement) markForAutoPip(event.target);
}

/* ---- Wiring ------------------------------------------------------------- */

function apply(next) {
  settings = next;
  paint();
  for (const video of document.querySelectorAll('video')) markForAutoPip(video);
  redirect();
}

document.addEventListener('yt-navigate-finish', redirect);
document.addEventListener('visibilitychange', onVisibilityChange);
document.addEventListener('play', onPlay, true);
document.addEventListener('leavepictureinpicture', () => { pipIsOurs = false; }, true);
window.addEventListener('blur', onBlur);
window.addEventListener('focus', onFocus);

// Changing a setting takes effect in every open tab, without a reload. The
// redirects are the exception by nature: they act on a navigation, so turning
// one on cannot retroactively move a page you are already looking at.
api.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local' || !settings) return;
  const merged = { ...settings };
  for (const [key, { newValue }] of Object.entries(changes)) merged[key] = newValue;
  settings = globalThis.NTR.normalise(merged);
  paint();
  for (const video of document.querySelectorAll('video')) markForAutoPip(video);
});

globalThis.NTR.read().then(apply);
