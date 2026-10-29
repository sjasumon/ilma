// Only public shell/assets and bank GET responses. No audio uploads or user data.
const SHELL = 'ilma-shell-voice57';
const BANKS = 'ilma-public-banks-v1';
const ASSETS = ["/static/fonts/fonts.css?v=voice-complete-20261029-57", "/static/fonts/noto-sans-bengali-bengali-2.woff2", "/static/fonts/noto-sans-bengali-latin-3.woff2", "/static/fonts/noto-sans-latin-1.woff2", "/static/fonts/tiro-bangla-bengali-4.woff2", "/static/fonts/tiro-bangla-latin-5.woff2", '/', '/static/css/ilma.css?v=voice-complete-20261029-57', '/static/js/ivr.js?v=voice-complete-20261029-57', '/static/js/voice-agent.js?v=voice-complete-20261029-57', '/static/js/app.js?v=voice-complete-20261029-57', '/static/js/bank-services-ui.js?v=voice-complete-20261029-57', '/static/js/audio-session.js?v=voice-complete-20261029-57', '/static/js/voice-recorder.js?v=voice-complete-20261029-57'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('ilma-shell-') && key !== SHELL).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  const bank = (url.pathname === '/v1/institutions' && url.searchParams.get('list') === 'demo') || /^\/v1\/institutions\/(?:index|[^/]+\/(?:report-card|figures|ratings|events|history|services))$/.test(url.pathname) || /^\/v1\/services\/(?:categories|compare|offers\/[^/]+)$/.test(url.pathname);
  const asset = url.pathname === '/' || url.pathname.startsWith('/static/');
  if (!bank && !asset && url.pathname !== '/v1/content/fixed') return;
  event.respondWith((async () => {
    const cache = await caches.open(bank ? BANKS : SHELL);
    try {
      const response = await fetch(request);
      if (response.ok) {
        await cache.put(request, response.clone());
        if (bank) {
          const keys = (await cache.keys()).filter(key => new URL(key.url).pathname !== '/v1/institutions/index');
          while (keys.length > 24) await cache.delete(keys.shift());
        }
      }
      return response;
    } catch (error) {
      const cached = await cache.match(request);
      if (!cached) throw error;
      if (!bank) return cached;
      const headers = new Headers(cached.headers); headers.set('X-ILMA-Offline', '1');
      return new Response(cached.body, { status: cached.status, headers });
    }
  })());
});
self.addEventListener('message', event => {
  if (event.data?.type !== 'cache-fixed-clips' || !Array.isArray(event.data.urls)) return;
  const urls = event.data.urls.filter(url => /^\/static\/audio\/fixed\/[a-zA-Z0-9_-]+\.(?:opus|mp3)$/.test(url));
  event.waitUntil(caches.open(SHELL).then(cache => cache.addAll(urls)));
});
