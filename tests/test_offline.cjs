const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
require('./test_catalog_recovery.cjs');
const handlers = new Map(), stores = new Map();
let offline = false;
let background=[];
const origin = 'https://ilma.test';
const key = request => new URL(typeof request === 'string' ? request : request.url, origin).href;
function store(name) {
  if (!stores.has(name)) stores.set(name, new Map());
  const data = stores.get(name);
  return {
    async put(request, response) { if(response.status===206)throw TypeError('Partial response cannot be cached');data.set(key(request), response.clone()); },
    async match(request) { return data.get(key(request))?.clone(); },
    async keys() { return [...data.keys()].map(url => new Request(url)); },
    async delete(request) { return data.delete(key(request)); },
    async addAll(urls) { for (const url of urls) data.set(key(url), new Response('asset')); }
  };
}
const context = vm.createContext({
  URL, Request, Response, Headers,
  self: { location: { origin }, addEventListener: (name, callback) => handlers.set(name, callback), skipWaiting: async () => {}, clients: { claim: async () => {} } },
  caches: { open: async name => store(name), keys: async () => [...stores.keys()], delete: async name => stores.delete(name) },
  fetch: async () => { if (offline) throw Error('offline'); return new Response('{"public":true}', { headers: {'Content-Type':'application/json'} }); }
});
vm.runInContext(fs.readFileSync('static/sw.js', 'utf8'), context);
async function request(path, method='GET') {
  let response;
  handlers.get('fetch')({ request: new Request(origin + path, { method }), respondWith(result) { response = result; }, waitUntil(result) { background.push(result); } });
  return response;
}
(async () => {
  await request('/v1/institutions/index');
  for (let i=1; i<=26; i++) await request(`/v1/institutions/${i}/report-card`);
  offline = true;
  const index = await request('/v1/institutions/index');
  assert.equal(index.headers.get('X-ILMA-Offline'), '1');
  const card = await request('/v1/institutions/26/report-card');
  assert.equal(card.headers.get('X-ILMA-Offline'), '1');
  assert.equal(await request('/v1/voice', 'POST'), undefined);
  assert.equal(await request('/v1/ask', 'POST'), undefined);
  assert.equal(await request('/.env'), undefined);
  assert.equal(await request('/v1/watch'), undefined);
  assert.equal((await store('ilma-public-banks-v1').keys()).length, 25);
  offline=false;
  const originalFetch=context.fetch;
  const catalogs=['/v1/services/accounts?product_type=account_fee&item=savings&audience=all','/v1/services/deposits?product_type=fdr&audience=all&basis=conventional'];
  for(const path of catalogs) {
    assert.equal((await request(path)).status,200);
    const stored=await store('ilma-public-banks-v1').match(origin+path);
    const timestamp=stored.headers.get('X-ILMA-Cached-At');
    assert.ok(Number.isFinite(Date.parse(timestamp)),'Record when the saved public copy was downloaded');
    offline=true;
    const cached=await request(path);
    assert.equal(cached.headers.get('X-ILMA-Offline'),'1');
    assert.equal(cached.headers.get('X-ILMA-Cached-At'),timestamp,'Offline reads do not refresh saved time');
    offline=false;context.fetch=async()=>new Response('server outage',{status:503});
    const outage=await request(path);
    assert.equal(outage.status,200);assert.equal(outage.headers.get('X-ILMA-Offline'),'1');
    assert.equal(outage.headers.get('X-ILMA-Cached-At'),timestamp);
    context.fetch=async()=>new Response('removed',{status:404});
    assert.equal((await request(path)).status,404,'Never mask removed or forbidden resources with old data');
    context.fetch=originalFetch;
  }
  assert.equal(await request('/v1/services/accounts?balance=125000'),undefined);
  assert.equal(await request('/v1/services/deposits?amount=125000'),undefined);
  assert.equal(await request('/v1/services/compare?product_type=home_loan&amount=125000'),undefined);
  assert.equal(await request('/v1/audio/synthetic.mp3'),undefined);
  offline=false;

  context.fetch=async()=>new Response('audio',{status:206,headers:{'Content-Type':'audio/mpeg','Content-Range':'bytes 0-4/5'}});
  let media=await request('/static/audio/services/bn/card-visa-gold.mp3?v=aaaaaaaaaaaaaaaa');
  assert.equal(media.status,206,'Range response must reach the player unchanged');
  await Promise.all(background);background=[];
  offline=true;context.fetch=async()=>{throw Error('offline')};
  media=await request('/static/audio/services/bn/card-visa-gold.mp3?v=aaaaaaaaaaaaaaaa');
  assert.equal(media.status,200);assert.equal(await media.text(),'audio');
  assert.equal(media.headers.get('Content-Range'),null);
  offline=false;context.fetch=async()=>new Response('part',{status:206,headers:{'Content-Range':'bytes 3-6/9'}});
  media=await request('/static/audio/services/bn/card-visa-classic.mp3?v=bbbbbbbbbbbbbbbb');assert.equal(media.status,206);
  assert.equal(await store('ilma-service-audio-v1').match(origin+'/static/audio/services/bn/card-visa-classic.mp3?v=bbbbbbbbbbbbbbbb'),undefined);
  context.fetch=async()=>new Response('bank',{status:206,headers:{'Content-Type':'audio/mpeg','Content-Range':'bytes 0-3/4'}});
  media=await request('/static/audio/bank/bn/synthetic.mp3?v=cccccccccccccccc');assert.equal(media.status,206);
  await Promise.all(background);background=[];context.fetch=async()=>{throw Error('offline')};
  media=await request('/static/audio/bank/bn/synthetic.mp3?v=cccccccccccccccc');assert.equal(media.status,200);assert.equal(await media.text(),'bank');
  for (const path of ['/static/audio/services/bn/loan_home.mp3?v=ffffffffffffffff','/static/audio/services/bn/deposit_fdr-12-all.mp3?v=dddddddddddddddd','/static/audio/bank/bn/synthetic_bank.mp3?v=eeeeeeeeeeeeeeee']) {
    context.fetch=async()=>new Response('saved',{headers:{'Content-Type':'audio/mpeg'}});
    assert.equal((await request(path)).status,200);
    await Promise.all(background);background=[];
    context.fetch=async()=>{throw Error('offline')};
    assert.equal(await (await request(path)).text(),'saved','Approved deposit and underscore bank paths cache for offline playback');
  }
  context.fetch=originalFetch;
  console.log('Saved audio cache passed: 206 streaming, complete background caching, offline playback and incomplete ranges excluded');
  console.log('Offline cache passed: public index retained, report cap, stale marker, no uploads/private endpoints cached');
})().catch(error => { console.error(error); process.exitCode = 1; });
