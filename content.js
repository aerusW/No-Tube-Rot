// Handles SPA navigation: declarativeNetRequest catches hard loads,
// this catches YouTube's internal router navigating back to the homepage.
function redirectIfHome() {
  if (/^https:\/\/www\.youtube\.com\/?(\?[^#]*)?$/.test(location.href)) {
    location.replace('https://www.youtube.com/feed/subscriptions');
  }
}

redirectIfHome();

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

// Re-check on every navigation in case the element was removed by YouTube's renderer
document.addEventListener('yt-navigate-finish', () => {
  redirectIfHome();
  initSessionTimer();
});

document.addEventListener('DOMContentLoaded', initSessionTimer);
