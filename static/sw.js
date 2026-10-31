// Only public shell/assets and bank GET responses. No audio uploads or user data.
const SHELL = 'ilma-shell-48544added6c3308';
const SERVICE_AUDIO = 'ilma-service-audio-v1';
const BANKS = 'ilma-public-banks-v1';
const ASSETS = ['/static/js/navigation.js?v=sha256-15fbf488d620b394','/static/js/account-ui.js?v=sha256-4bb9fc68f13503c8','/static/js/deposit-ui.js?v=sha256-f5b5a727841bcd79','/static/js/loan-ui.js?v=sha256-1be11d9cfd18bb3e','/static/js/catalog-common.js?v=sha256-ba956ab9c1dd4d5a','/static/js/bank-ui.js?v=sha256-d79f803b974836ca','/static/js/services-ui.js?v=sha256-5efac29c1612bfd9',"/static/fonts/fonts.css?v=sha256-7e786499b46bb84c", "/static/fonts/noto-sans-bengali-bengali-2.woff2", "/static/fonts/noto-sans-bengali-latin-3.woff2", "/static/fonts/noto-sans-latin-1.woff2", "/static/fonts/tiro-bangla-bengali-4.woff2", "/static/fonts/tiro-bangla-latin-5.woff2", '/', '/static/css/ilma.css?v=sha256-e73d5e2382a42576', '/static/js/ivr.js?v=sha256-2929c97da156ab49', '/static/js/voice-agent.js?v=sha256-d20001d6aede81d8', '/static/js/app.js?v=sha256-5afc8250df562a70', '/static/js/bank-services-ui.js?v=sha256-ec1eb596f7b72cfd', '/static/js/audio-session.js?v=sha256-5054f0d844b15ef6', '/static/js/voice-recorder.js?v=sha256-cdbba7f8df091a23'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('ilma-shell-') && key !== SHELL).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  const publicQuery = [...url.searchParams.keys()].every(key => ['list','product_type','audience','basis','item','tenor_months','attribute','network','tier','compare_by','page','topic'].includes(key));
  const bank = publicQuery && ((url.pathname === '/v1/institutions' && url.searchParams.get('list') === 'demo') || /^\/v1\/institutions\/(?:index|[^/]+\/(?:report-card|figures|ratings|events|history|services))$/.test(url.pathname) || /^\/v1\/services\/(?:categories|audio-manifest|accounts|deposits|compare|offers\/[^/]+)$/.test(url.pathname));
  const asset = url.pathname === '/' || url.pathname.startsWith('/static/');
  if (!bank && !asset && url.pathname !== '/v1/content/fixed') return;
  event.respondWith((async () => {
    const serviceAudio=/^\/static\/audio\/(?:services\/bn\/(?:card-|deposit_|loan_)[a-z0-9-]+|(?:bank|loans|deposits|accounts)\/bn\/[a-z0-9_-]+)\.mp3$/.test(url.pathname);
    let cache;
    try { cache = await caches.open(serviceAudio ? SERVICE_AUDIO : bank ? BANKS : SHELL); }
    catch (_) { return fetch(request); }
    async function savedResponse() {
      let cached;
      try { cached = await cache.match(request); } catch (_) { return null; }
      if (!cached) return null;
      if (!bank) return cached;
      const headers = new Headers(cached.headers); headers.set('X-ILMA-Offline', '1');
      return new Response(cached.body, {status: cached.status, headers});
    }
    try {
      const response = await fetch(request);
      // Public data may use its dated saved copy during a server outage too.
      // Do not mask 4xx responses (removed/forbidden resources).
      if (bank && response.status >= 500) {
        const saved = await savedResponse();
        if (saved) return saved;
      }
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
          const copy = response.clone();
          if (bank) {
            const headers = new Headers(copy.headers);
            headers.set('X-ILMA-Cached-At', new Date().toISOString());
            await cache.put(request, new Response(copy.body, {status: copy.status, headers}));
          } else await cache.put(request, copy);
          if (bank) {
            const keys = (await cache.keys()).filter(key => new URL(key.url).pathname !== '/v1/institutions/index');
            while (keys.length > 24) await cache.delete(keys.shift());
          }
        } catch (_) {}
      }
      return response;
    } catch (error) {
      const cached = await savedResponse();
      if (!cached) throw error;
      return cached;
    }
  })());
});
self.addEventListener('message', event => {
  if (event.data?.type !== 'cache-fixed-clips' || !Array.isArray(event.data.urls)) return;
  const urls = event.data.urls.filter(url => /^\/static\/audio\/fixed\/[a-zA-Z0-9_-]+\.(?:opus|mp3)$/.test(url));
  event.waitUntil(caches.open(SHELL).then(cache => cache.addAll(urls)));
});
