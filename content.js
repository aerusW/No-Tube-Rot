// Handles SPA navigation: declarativeNetRequest catches hard loads, this
// catches YouTube's internal router. The two are intentionally redundant so
// the redirects hold whether you type/click a URL or navigate in-app.
function redirect() {
  const path = location.pathname;

  // Homepage -> subscriptions feed.
  if (path === '/') {
    location.replace('https://www.youtube.com/feed/subscriptions');
    return;
  }

  // Shorts feed (no video id) -> subscriptions feed.
  if (path === '/shorts' || path === '/shorts/') {
    location.replace('https://www.youtube.com/feed/subscriptions');
    return;
  }

  // A specific Short -> the same video in the normal player.
  const short = path.match(/^\/shorts\/([\w-]+)/);
  if (short) {
    location.replace('https://www.youtube.com/watch?v=' + short[1]);
    return;
  }
}

redirect();
document.addEventListener('yt-navigate-finish', redirect);
