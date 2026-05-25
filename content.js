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

  // Remove the two-column attribute so the layout fills the full width
  const watch = document.querySelector('ytd-watch-flexy');
  if (watch) watch.removeAttribute('is-two-columns_');

  // Turn off autoplay if it's currently on
  const autoplayBtn = document.querySelector('.ytp-autonav-toggle-button[aria-checked="true"]');
  if (autoplayBtn) autoplayBtn.click();
}

// Retry until the player is ready (YouTube mounts it asynchronously)
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
document.addEventListener('yt-navigate-finish', () => {
  redirectIfHome();
  setupWatchPageWhenReady();
});
