// Only public shell/assets and bank GET responses. No audio uploads or user data.
const SHELL = 'ilma-shell-d9325342decb2b51';
const SERVICE_AUDIO = 'ilma-service-audio-v1';
const BANKS = 'ilma-public-banks-v1';
const ASSETS = ['/static/js/navigation.js?v=sha256-af89eb2c066f5aeb','/static/js/account-ui.js?v=sha256-2557a03d31051b83','/static/js/deposit-ui.js?v=sha256-738a5547971d7276','/static/js/loan-ui.js?v=sha256-f4186b981cbff2c1','/static/js/catalog-common.js?v=sha256-0656a46f9f31436a','/static/js/bank-ui.js?v=sha256-69f9de1e3f34fef6','/static/js/services-ui.js?v=sha256-d33af839d9312991',"/static/fonts/fonts.css?v=sha256-7e786499b46bb84c", "/static/fonts/noto-sans-bengali-bengali-2.woff2", "/static/fonts/noto-sans-bengali-latin-3.woff2", "/static/fonts/noto-sans-latin-1.woff2", "/static/fonts/tiro-bangla-bengali-4.woff2", "/static/fonts/tiro-bangla-latin-5.woff2", '/', '/static/css/ilma.css?v=sha256-583c1f7a6163cf23', '/static/js/ivr.js?v=sha256-2929c97da156ab49', '/static/js/voice-agent.js?v=sha256-e9de418dd1b76828', '/static/js/app.js?v=sha256-8f7de19bd814d073', '/static/js/bank-services-ui.js?v=sha256-ec1eb596f7b72cfd', '/static/js/audio-session.js?v=sha256-5c97cf7474d94c72', '/static/js/voice-recorder.js?v=sha256-45d728097d4d8341'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('ilma-shell-') && key !== SHELL).map(key => caches.delete(key)))).then(() => self.clients.claim()).then(() => maintainAudio()));
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  const publicQuery = [...url.searchParams.keys()].every(key => ['list','product_type','audience','basis','item','tenor_months','attribute','network','tier','compare_by','page','topic'].includes(key));
  const bank = publicQuery && ((url.pathname === '/v1/institutions' && url.searchParams.get('list') === 'demo') || /^\/v1\/institutions\/(?:index|[^/]+\/(?:report-card|figures|ratings|events|history|services))$/.test(url.pathname) || /^\/v1\/services\/(?:categories|audio-manifest|accounts|deposits|compare|offers\/[^/]+)$/.test(url.pathname));
  const asset = url.pathname === '/' || url.pathname.startsWith('/static/');
  if (!bank && !asset && url.pathname !== '/v1/content/fixed') return;
  event.respondWith((async () => {
    const serviceAudio=/^\/static\/audio\/(?:services\/bn\/(?:card-|deposit_|loan_)[a-z0-9-]+|(?:bank|loans|deposits|accounts|news|answers)\/(?:bn|en)\/[a-z0-9_-]+|(?:bank|loans|deposits|accounts)\/bn\/[a-z0-9_-]+)\.mp3$/.test(url.pathname);
    let cache;
    try { if (!serviceAudio) cache = await caches.open(bank ? BANKS : SHELL); }
    catch (_) { return fetch(request); }
    async function savedResponse() {
      let cached;
      try { if (!cache) cache = await caches.open(SERVICE_AUDIO); cached = await cache.match(request); } catch (_) { return null; }
      if (!cached) return null;
      if (serviceAudio) {
        const copy = cached.clone();
        event.waitUntil(queueAudio(() => touchAudio(new Request(request.url), copy)));
      }
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
          event.waitUntil(queueAudio(() => storeAudio(new Request(request.url), full)));
        }
        return response;
      }
      const manifestScope = AUDIO_MANIFESTS.find(([path]) => path === url.pathname)?.[1];
      if (manifestScope && response.ok) {
        const fresh = response.clone();
        event.waitUntil(queueAudio(() => applyAudioManifest(fresh, manifestScope)));
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

// Listened clips only: bounded, best-effort storage, never a full offline bundle.
const AUDIO_META = 'ilma-service-audio-meta-v1';
const AUDIO_MAX_BYTES = 32 * 1024 * 1024;
const AUDIO_MAX_ENTRIES = 40;
const AUDIO_MANIFESTS = [
  ['/v1/services/audio-manifest', '/static/audio/services/'],
  ['/static/audio/bank/manifest.json', '/static/audio/bank/'],
  ['/static/audio/accounts/manifest.json', '/static/audio/accounts/'],
  ['/static/audio/answers/manifest.json', '/static/audio/answers/']
];
let audioQueue = Promise.resolve(), audioClock = 0;
const currentAudio = new Map();
const usedNow = () => audioClock = Math.max(Date.now(), audioClock + 1);
function queueAudio(work) {
  // Serialize writes/touches/eviction across simultaneous media requests.
  audioQueue = audioQueue.then(work).catch(() => {});
  return audioQueue;
}
async function audioStores() { return Promise.all([caches.open(SERVICE_AUDIO), caches.open(AUDIO_META)]); }
async function metadata(meta, request) {
  try {
    const data = await (await meta.match(request)).json();
    if (Number.isSafeInteger(data.bytes) && data.bytes > 0 && Number.isFinite(data.used)) return data;
  } catch (_) {}
  return null;
}
async function saveMetadata(meta, request, data) {
  try { await meta.put(request, new Response(JSON.stringify(data), {headers: {'Content-Type':'application/json'}})); } catch (_) {}
}
async function pruneAudio(cache, meta) {
  const entries = [], live = new Set();
  let total = 0;
  for (const request of await cache.keys()) {
    const response = await cache.match(request);
    if (!response) continue;
    live.add(request.url);
    let data = await metadata(meta, request);
    if (!data) {
      // Legacy entries have no trusted byte count; measure them once in background.
      data = {bytes: (await response.arrayBuffer()).byteLength, used: 0};
      await saveMetadata(meta, request, data);
    }
    entries.push({request, ...data}); total += data.bytes;
  }
  entries.sort((a,b) => a.used - b.used);
  let count = entries.length;
  for (const entry of entries) {
    if (count <= AUDIO_MAX_ENTRIES && total <= AUDIO_MAX_BYTES) break;
    await cache.delete(entry.request); await meta.delete(entry.request);
    live.delete(entry.request.url); total -= entry.bytes; count--;
  }
  for (const request of await meta.keys()) if (!live.has(request.url)) await meta.delete(request);
}
function audioScope(url) {
  return AUDIO_MANIFESTS.find(([,scope]) => new URL(url).pathname.startsWith(scope))?.[1];
}
async function storeAudio(request, response) {
  const [cache, meta] = await audioStores(), scope = audioScope(request.url);
  if (scope && currentAudio.has(scope) && !currentAudio.get(scope).has(request.url)) return;
  const bytes = await response.arrayBuffer();
  if (!bytes.byteLength || bytes.byteLength > AUDIO_MAX_BYTES) return;
  await cache.put(request, new Response(bytes, {status:200, headers:response.headers}));
  await saveMetadata(meta, request, {bytes:bytes.byteLength, used:usedNow()});
  await pruneAudio(cache, meta);
}
async function touchAudio(request, response) {
  const [cache, meta] = await audioStores();
  const data = await metadata(meta, request) || {bytes:(await response.arrayBuffer()).byteLength};
  await saveMetadata(meta, request, {...data, used:usedNow()});
  await pruneAudio(cache, meta);
}
async function applyAudioManifest(response, scope) {
  if (!response.ok || response.headers.get('X-ILMA-Offline') === '1') return;
  let data;
  try { data = await response.json(); } catch (_) { return; }
  if (!data || typeof data.clips !== 'object' || Array.isArray(data.clips) || !data.clips) return;
  const clips = Object.values(data.clips), urls = new Set();
  // An empty/error/partial malformed response is not evidence to erase saved clips.
  if (!clips.length || data.batch_complete === false || (data.remaining_clips != null && data.remaining_clips !== 0) || (Number.isSafeInteger(data.expected_clips) && clips.length < data.expected_clips)) return;
  for (const clip of clips) {
    if (!clip || clip.reviewed !== true || !/^[a-f0-9]{64}$/.test(clip.audio_sha256 || '') || typeof clip.file !== 'string') return;
    const path = clip.file.startsWith('static/audio/') ? '/' + clip.file : scope + clip.file;
    if (!path.startsWith(scope) || !/^\/static\/audio\/(?:services|bank|accounts)\/bn\/[a-z0-9_-]+\.mp3$/.test(path)) return;
    urls.add(new URL(path + '?v=' + clip.audio_sha256.slice(0,16), self.location.origin).href);
  }
  currentAudio.set(scope, urls);
  const [cache, meta] = await audioStores();
  for (const request of await cache.keys()) {
    if (new URL(request.url).pathname.startsWith(scope) && !urls.has(request.url)) {
      await cache.delete(request); await meta.delete(request);
    }
  }
  await pruneAudio(cache, meta);
}
async function maintainAudio() {
  // Fetch JSON only; never preload recordings. A failed manifest retains saved audio.
  let savedAccounts = false;
  try {
    const cache = await caches.open(SERVICE_AUDIO);
    savedAccounts = (await cache.keys()).some(request => new URL(request.url).pathname.startsWith('/static/audio/accounts/'));
  } catch (_) {}
  const requested = AUDIO_MANIFESTS.filter(([,scope]) => scope !== '/static/audio/accounts/' || savedAccounts);
  const manifests = await Promise.all(requested.map(async ([url,scope]) => {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 4000);
    try {
      const response = await fetch(new Request(new URL(url,self.location.origin), {cache:'no-store',signal:controller.signal}));
      if (!response.ok) return [null,scope];
      const bytes = await response.arrayBuffer();
      return [new Response(bytes,{status:response.status,headers:response.headers}),scope];
    } catch (_) { return [null,scope]; }
    finally { clearTimeout(timer); }
  }));
  await queueAudio(async () => {
    const [cache, meta] = await audioStores(); await pruneAudio(cache,meta);
    for (const [response,scope] of manifests) if (response) await applyAudioManifest(response,scope);
  });
}
