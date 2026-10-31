// Execute real request/retry paths; personal calculator values stay in memory.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const nodes=new Map();
const node=id=>{
  if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',hidden:false,disabled:false,style:{},querySelector:selector=>node(id+selector),querySelectorAll:()=>[],addEventListener(){}});
  return nodes.get(id);
};
let network=false,mounted=null,seen=[];
const c=vm.createContext({
  URLSearchParams,Intl,Date,console,
  currentLang:'bn',currentTab:'services',escapeHTML:String,toBnDigits:String,
  document:{getElementById:node},
  stopAudio(){},switchTab(){},
  fetch:async url=>{
    seen.push(String(url));
    if(url==='/v1/services/categories')return {ok:true,json:async()=>[]};
    if(!network)throw TypeError('Load failed: PRIVATE_BROWSER_DETAIL');
    return {ok:true,headers:{get:()=>null},json:async()=>({choice:{product_type:'fdr'},catalog_banks:[],readouts:{}})};
  },
  window:{IlmaNavigation:{visit(){}},IlmaDeposits:{mount(data,hooks,prefill){mounted={data,hooks,prefill};}},IlmaLoans:{types:[]}}
});
vm.runInContext(fs.readFileSync('static/js/catalog-common.js','utf8'),c);
vm.runInContext(fs.readFileSync('static/js/services-ui.js','utf8'),c);
const run=code=>vm.runInContext(code,c);
(async()=>{
  await run("window.IlmaServices.openComparison({product_type:'fdr',audience:'senior'},{amount:234567,term:24,fromVoice:true})");
  const failedURL=seen.find(url=>url.startsWith('/v1/services/deposits?'));
  assert.ok(failedURL.includes('audience=senior'));
  assert.ok(!failedURL.includes('234567'),'Entered amount must not enter the request');
  assert.ok(!node('services-catalog').innerHTML.includes('PRIVATE_BROWSER_DETAIL'));
  assert.match(node('services-catalog').innerHTML,/তথ্য আনা যায়নি/);
  network=true;
  await node('services-catalog[data-retry]').onclick();
  assert.ok(mounted,'Retry must reopen the original calculator, not the Services home');
  assert.equal(mounted.prefill.amount,234567);
  assert.equal(mounted.prefill.term,24);
  assert.equal(mounted.prefill.audience,'senior');
  assert.equal(seen.filter(url=>url.startsWith('/v1/services/deposits?')).at(-1),failedURL);
  c.currentLang='en';
  const common=c.window.IlmaCatalogCommon;
  common.error(node('example'),Error('Failed to fetch'),()=>{});
  assert.match(node('example').innerHTML,/Check your connection/);
  assert.ok(!node('example').innerHTML.includes('Failed to fetch'));
  assert.equal(common.offlineNote({}), '');
  const dated=common.offlineNote({_offline:true,_cachedAt:'2026-10-31T08:15:00Z'});
  assert.match(dated,/Saved copy/);assert.match(dated,/2026/);assert.match(dated,/Check the source document dates/);
  assert.ok(!common.offlineNote({_offline:true,_cachedAt:'invalid'}).includes('Invalid Date'));
  c.fetch=async()=>({ok:true,headers:{get:key=>key==='X-ILMA-Offline'?'1':key==='X-ILMA-Cached-At'?'2026-10-31T08:15:00Z':null},json:async()=>({banks:[]})});
  const copy=await common.json('/v1/services/accounts');
  assert.equal(copy._offline,true);assert.equal(copy._cachedAt,'2026-10-31T08:15:00Z');
  console.log('Catalog recovery passed: localized error, same-operation retry, memory-only values and dated offline copy');
})().catch(e=>{console.error(e);process.exitCode=1;});
