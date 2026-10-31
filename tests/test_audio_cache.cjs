// Reduced storage budgets exercise the real worker policy using synthetic bytes.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('static/sw.js','utf8');
assert.match(source,/const AUDIO_MAX_BYTES = 32 \* 1024 \* 1024/);
assert.match(source,/const AUDIO_MAX_ENTRIES = 40/);
function fixture(){
 const handlers=new Map(),data=new Map(),fetched=[];let pending=[],fetcher=async()=>new Response('1234'),block=null,quota=false;
 const origin='https://audio.test',key=request=>new URL(typeof request==='string'?request:request.url,origin).href;
 function cache(name){
  if(!data.has(name))data.set(name,new Map());const entries=data.get(name);
  return {async keys(){return [...entries.keys()].map(url=>new Request(url));},async match(r){return entries.get(key(r))?.clone();},async delete(r){return entries.delete(key(r));},async addAll(){},async put(r,response){if(name==='ilma-service-audio-v1'&&block)await block;if(quota)throw Error('QuotaExceededError');assert.notEqual(response.status,206);entries.set(key(r),response.clone());}};
 }
 const context=vm.createContext({URL,Request,Response,Headers,AbortController,setTimeout,clearTimeout,console,self:{location:{origin},addEventListener:(name,callback)=>handlers.set(name,callback),clients:{claim:async()=>{}},skipWaiting:async()=>{}},caches:{open:async name=>cache(name),keys:async()=>[...data.keys()],delete:async name=>data.delete(name)},fetch:request=>{fetched.push(new URL(request.url).pathname);return fetcher(request);}});
 vm.runInContext(source.replace('32 * 1024 * 1024','12').replace('const AUDIO_MAX_ENTRIES = 40','const AUDIO_MAX_ENTRIES = 3'),context);
 async function request(path){let response;handlers.get('fetch')({request:new Request(origin+path),respondWith(r){response=r;},waitUntil(p){pending.push(p);}});return response;}
 async function drain(){while(pending.length){const jobs=pending;pending=[];await Promise.all(jobs);}}
 return {context,cache,request,drain,fetched,fetch(fn){fetcher=fn;},setBlock(value){block=value;},setQuota(value){quota=value;},activate(){handlers.get('activate')({waitUntil(p){pending.push(p);}});}};
}
const path=(name,version='a')=>'/static/audio/services/bn/card-'+name+'.mp3?v='+version.repeat(16);
async function keys(f){return (await f.cache('ilma-service-audio-v1').keys()).map(x=>new URL(x.url).pathname);}
(async()=>{
 let f=fixture();
 await Promise.all(['one','two','three','four','five'].map(name=>f.request(path(name))));await f.drain();
 assert.equal((await keys(f)).length,3,'Concurrent writes respect the entry cap after background work completes');
 let sum=0;for(const request of await f.cache('ilma-service-audio-v1').keys())sum+=(await (await f.cache('ilma-service-audio-v1').match(request)).arrayBuffer()).byteLength;
 assert.ok(sum<=12,'Concurrent writes respect measured bytes');
 f=fixture();for(const name of ['one','two','three']){await f.request(path(name));await f.drain();}
 f.fetch(async()=>{throw Error('offline');});assert.equal((await f.request(path('one'))).status,200);await f.drain();
 f.fetch(async()=>new Response('1234'));await f.request(path('four'));await f.drain();
 assert.ok((await keys(f)).some(x=>x.endsWith('card-one.mp3')),'An offline read touches the persistent LRU');
 assert.ok(!(await keys(f)).some(x=>x.endsWith('card-two.mp3')),'Least recently used clip evicted');
 f.fetch(async()=>new Response('123456789'));await f.request(path('large'));await f.drain();
 assert.deepEqual(await keys(f),['/static/audio/services/bn/card-large.mp3'],'Byte cap can evict multiple small clips');
 f=fixture();let release;f.setBlock(new Promise(r=>{release=r;}));
 const response=await Promise.race([f.request(path('stream')),new Promise((_,reject)=>setTimeout(()=>reject(Error('Media waited for storage')),500))]);
 assert.equal(await response.text(),'1234','Network media reaches the player while cache.put is blocked');
 release();f.setBlock(null);await f.drain();
 f.setQuota(true);assert.equal((await f.request(path('quota'))).status,200);await f.drain();
 f=fixture();await f.request(path('old'));await f.drain();
 const manifest='/v1/services/audio-manifest';
 f.fetch(async()=>new Response(JSON.stringify({clips:{entry:{file:'bn/card-old.mp3',reviewed:true,audio_sha256:'b'.repeat(64)}}}),{headers:{'Content-Type':'application/json'}}));
 await f.request(manifest);await f.drain();assert.deepEqual(await keys(f),[],'Successful valid current manifest prunes the obsolete hash');
 f.fetch(async()=>new Response('1234'));await f.request(path('old','b'));await f.drain();assert.equal((await keys(f)).length,1);
 await f.request(path('old','a'));await f.drain();assert.equal((await f.cache('ilma-service-audio-v1').keys()).length,1,'A late old response cannot reinsert an obsolete hash');
 for(const payload of [{clips:{}},{clips:{entry:{file:'bn/card-other.mp3',reviewed:false,audio_sha256:'c'.repeat(64)}}},{batch_complete:true,remaining_clips:1,clips:{entry:{file:'bn/card-other.mp3',reviewed:true,audio_sha256:'c'.repeat(64)}}},{clips:{entry:{file:'../escape.mp3',reviewed:true,audio_sha256:'b'.repeat(64)}}},{batch_complete:false,clips:{entry:{file:'bn/card-other.mp3',reviewed:true,audio_sha256:'c'.repeat(64)}}}]){
  f.fetch(async()=>new Response(JSON.stringify(payload)));await f.request(manifest);await f.drain();assert.equal((await keys(f)).length,1,'Malformed/empty/incomplete manifests retain valid clips');
 }
 f.fetch(async()=>new Response('outage',{status:503}));await f.request(manifest);await f.drain();assert.equal((await keys(f)).length,1,'Failed manifest cannot erase saved audio');
 f=fixture();f.fetch(async()=>new Response('{}'));f.activate();await f.drain();assert.ok(!f.fetched.includes('/static/audio/accounts/manifest.json'),'Do not request an absent optional accounts bundle at startup');
 await f.cache('ilma-service-audio-v1').put('https://audio.test/static/audio/accounts/bn/example.mp3?v='+'a'.repeat(16),new Response('1234'));f.activate();await f.drain();assert.ok(f.fetched.includes('/static/audio/accounts/manifest.json'),'Existing accounts audio enables its optional manifest cleanup');
 f=fixture();for(const name of ['legacy1','legacy2','legacy3','legacy4'])await f.cache('ilma-service-audio-v1').put('https://audio.test'+path(name),new Response('1234'));
 f.fetch(async()=>{throw Error('offline');});f.activate();await f.drain();assert.equal((await keys(f)).length,3,'Activation bounds legacy caches even when all manifests are unavailable');
 f.context.setTimeout=callback=>{queueMicrotask(callback);return 0;};f.context.clearTimeout=()=>{};
 f.fetch(request=>new Promise((_,reject)=>request.signal.addEventListener('abort',()=>reject(Error('deadline')))));
 f.activate();await f.drain();assert.equal((await keys(f)).length,3,'Hung activation manifests are bounded and do not erase valid clips');
 f.fetch(async()=>{throw Error('offline');});
 // Persistent metadata also bounds a legacy cache on an offline hit.
 await f.cache('ilma-service-audio-v1').put('https://audio.test'+path('legacy5'),new Response('1234'));await f.request(path('legacy5'));await f.drain();assert.equal((await keys(f)).length,3);
 assert.equal((await f.cache('ilma-service-audio-meta-v1').keys()).length,3,'Eviction removes orphaned usage metadata');
 console.log('Audio storage passed: byte/entry limits, persistent LRU, concurrent writes, manifest cleanup/failure, legacy bounds and nonblocking playback');
})().catch(e=>{console.error(e);process.exitCode=1;});
