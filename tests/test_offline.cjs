const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const handlers = new Map(), stores = new Map();
let offline = false;
const origin = 'https://ilma.test';
const key = request => new URL(typeof request === 'string' ? request : request.url, origin).href;
function store(name) {
  if (!stores.has(name)) stores.set(name, new Map());
  const data = stores.get(name);
  return {
    async put(request, response) { data.set(key(request), response.clone()); },
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
  handlers.get('fetch')({ request: new Request(origin + path, { method }), respondWith(result) { response = result; } });
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
  console.log('Offline cache passed: public index retained, report cap, stale marker, no uploads/private endpoints cached');
})().catch(error => { console.error(error); process.exitCode = 1; });
