/* Native app glue. Runs only inside the Capacitor app; no effect in a browser. */
(function () {
  const cap = window.Capacitor;
  if (!cap?.isNativePlatform?.()) return;
  const { App, Browser, StatusBar } = cap.Plugins || {};

  // B6: Handle back button press
  if (App) {
    App.addListener('backButton', () => {
      if (window.ilmaGoBack && window.ilmaGoBack()) return; // handled inside the page
      App.exitApp();
    });
  }

  // B7: Intercept external link clicks to open in Chrome Custom Tab / In-App Browser
  document.addEventListener('click', (event) => {
    const a = event.target.closest?.('a[href]');
    if (!a) return;
    const url = new URL(a.href, location.href);
    if (url.origin === location.origin || !/^https?:$/.test(url.protocol)) return;
    event.preventDefault();
    if (Browser) {
      Browser.open({ url: url.href });
    } else {
      window.open(url.href, '_blank');
    }
  }, true);

  // B8: Status bar configuration
  if (StatusBar) {
    StatusBar.setBackgroundColor({ color: '#0F2624' }).catch(() => {});
    StatusBar.setStyle({ style: 'DARK' }).catch(() => {});
  }
})();
