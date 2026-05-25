// Handles SPA navigation: declarativeNetRequest catches hard loads,
// this catches YouTube's internal router navigating back to the homepage.
function redirectIfHome() {
  if (/^https:\/\/www\.youtube\.com\/?(\?[^#]*)?$/.test(location.href)) {
    location.replace('https://www.youtube.com/feed/subscriptions');
  }
}

redirectIfHome();
document.addEventListener('yt-navigate-finish', redirectIfHome);
