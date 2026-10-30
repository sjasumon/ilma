// Only public shell/assets and bank GET responses. No audio uploads or user data.
const SHELL = 'ilma-shell-9017425cb50b9223';
const SERVICE_AUDIO = 'ilma-service-audio-v1';
const BANKS = 'ilma-public-banks-v1';
const ASSETS = ['/static/js/catalog-common.js?v=sha256-0b2e5985c81e8b3e','/static/js/bank-ui.js?v=sha256-fb21a5eca07916fd','/static/js/services-ui.js?v=sha256-2619a49713ed625b',"/static/fonts/fonts.css?v=sha256-7e786499b46bb84c", "/static/fonts/noto-sans-bengali-bengali-2.woff2", "/static/fonts/noto-sans-bengali-latin-3.woff2", "/static/fonts/noto-sans-latin-1.woff2", "/static/fonts/tiro-bangla-bengali-4.woff2", "/static/fonts/tiro-bangla-latin-5.woff2", '/', '/static/css/ilma.css?v=sha256-f374d0903e7d9600', '/static/js/ivr.js?v=sha256-2929c97da156ab49', '/static/js/voice-agent.js?v=sha256-d20001d6aede81d8', '/static/js/app.js?v=sha256-77f98f876df903f4', '/static/js/bank-services-ui.js?v=sha256-ec1eb596f7b72cfd', '/static/js/audio-session.js?v=sha256-5054f0d844b15ef6', '/static/js/voice-recorder.js?v=sha256-cdbba7f8df091a23'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('ilma-shell-') && key !== SHELL).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  const bank = (url.pathname === '/v1/institutions' && url.searchParams.get('list') === 'demo') || /^\/v1\/institutions\/(?:index|[^/]+\/(?:report-card|figures|ratings|events|history|services))$/.test(url.pathname) || /^\/v1\/services\/(?:categories|audio-manifest|compare|offers\/[^/]+)$/.test(url.pathname);
  const asset = url.pathname === '/' || url.pathname.startsWith('/static/');
  if (!bank && !asset && url.pathname !== '/v1/content/fixed') return;
  event.respondWith((async () => {
    const serviceAudio=/^\/static\/audio\/services\/bn\/card-[a-z0-9-]+\.mp3$/.test(url.pathname);
    const cache = await caches.open(serviceAudio ? SERVICE_AUDIO : bank ? BANKS : SHELL);
    try {
      const response = await fetch(request);
      if (serviceAudio && response.ok) {
        // CacheStorage rejects 206 responses. Keep the media response streaming
        // to the player; only cache a complete representation in the background.
        const range = response.headers.get('Content-Range')?.match(/^bytes (\d+)-(\d+)\/(\d+)$/);
        const complete = response.status === 200 || (response.status === 206 && range && Number(range[1]) === 0 && Number(range[2]) + 1 === Number(range[3]));
        if (complete) {
          const headers = new Headers(response.headers); headers.delete('Content-Range');
          const full = new Response(response.clone().body, { status: 200, headers });
          event.waitUntil(cache.put(new Request(request.url), full).catch(() => {}));
        }
        return response;
      }
      if (response.ok && response.status !== 206) {
        // Quota/storage failures must never turn a successful fetch into an error.
        try {
          await cache.put(request, response.clone());
          if (bank) {
            const keys = (await cache.keys()).filter(key => new URL(key.url).pathname !== '/v1/institutions/index');
            while (keys.length > 24) await cache.delete(keys.shift());
          }
        } catch (_) {}
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
