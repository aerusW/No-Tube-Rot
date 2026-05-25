// Handles SPA navigation: declarativeNetRequest catches hard loads,
// this catches YouTube's internal router navigating back to the homepage.
function redirectIfHome() {
  if (/^https:\/\/www\.youtube\.com\/?(\?[^#]*)?$/.test(location.href)) {
    location.replace('https://www.youtube.com/feed/subscriptions');
  }
}

redirectIfHome();

// ── Watch page: disable autoplay and collapse to single column ──
function setupWatchPage() {
  if (!location.pathname.startsWith('/watch')) return;

  const watch = document.querySelector('ytd-watch-flexy');
  if (watch) watch.removeAttribute('is-two-columns_');

  const autoplayBtn = document.querySelector('.ytp-autonav-toggle-button[aria-checked="true"]');
  if (autoplayBtn) autoplayBtn.click();
}

function setupWatchPageWhenReady() {
  if (!location.pathname.startsWith('/watch')) return;
  const interval = setInterval(() => {
    const btn = document.querySelector('.ytp-autonav-toggle-button');
    if (btn) {
      clearInterval(interval);
      setupWatchPage();
    }
  }, 200);
}

setupWatchPageWhenReady();

// ── Session timer ──
function initSessionTimer() {
  if (document.getElementById('yt-zen-timer')) return;

  const KEY = 'yt_zen_session_start';
  if (!sessionStorage.getItem(KEY)) sessionStorage.setItem(KEY, Date.now());

  const el = document.createElement('div');
  el.id = 'yt-zen-timer';
  document.body.appendChild(el);

  function update() {
    const mins = Math.floor((Date.now() - Number(sessionStorage.getItem(KEY))) / 60000);
    const hrs = Math.floor(mins / 60);
    el.textContent = hrs > 0 ? `${hrs}h ${mins % 60}m on YouTube` : `${mins}m on YouTube`;
  }

  update();
  setInterval(update, 60000);
}

document.addEventListener('yt-navigate-finish', () => {
  redirectIfHome();
  setupWatchPageWhenReady();
  initSessionTimer();
});

document.addEventListener('DOMContentLoaded', initSessionTimer);
