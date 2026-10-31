// Runtime regressions without a browser; layout still needs device verification.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
require('./test_loan_audio.cjs');
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    textContent: '', innerHTML: '', value: '', checked: true, style: {}, dataset: {},
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {}, addEventListener() {}, querySelectorAll() { return []; },
    replaceChildren() { this.innerHTML = ''; }, appendChild() {}, focus() {},
  });
  return elements.get(id);
}
const context = vm.createContext({
  document: { body: {style:{}}, getElementById: element, querySelector: element, querySelectorAll: () => [], addEventListener() {}, documentElement: {} },
  window: { scrollTo() {} }, navigator: {}, console, setTimeout: () => 1,
  clearTimeout() {}, clearInterval() {}, setInterval: () => 1,
});
vm.runInContext(fs.readFileSync('static/js/app.js', 'utf8'), context);
function run(code) { return vm.runInContext(code, context); }
run('updateLocalizedText()');
run('reportCardData = {institution: {name_bn: "নমুনা", name_en: "Sample", coverage: "licence_only"}, status: null, message_en: "No financial data"}; currentLang = "en"; renderReportCard()');
assert.equal(element('card-status-word').textContent, 'Not rated');
assert.equal(element('card-status-mark').textContent, '');
assert.equal(element('card-insurance-line').textContent, 'No financial data');
assert.equal(run('escapeHTML(\'<img src=x onerror="bad()">\')'), '&lt;img src=x onerror=&quot;bad()&quot;&gt;');
run('openProofModal("Source", "<script>bad()</script>", "javascript:bad()", 1, "2026")');
assert.equal(element('modal-link').style.display, 'none');
assert.ok(!element('modal-quote').innerHTML.includes('<script>'));
run('closeProofModal()');
element('ret-amt-input').value = '0';
element('ret-rate-input').value = '0';
run('calculateRealReturn()');
assert.ok(element('ret-result-box').innerHTML.includes('0'));
assert.ok(!element('ret-result-box').innerHTML.includes('NaN'));
console.log('Frontend runtime regressions passed');
const html = fs.readFileSync('static/index.html', 'utf8');
assert.match(html, /id="home-listening-view" hidden/);
for (const asset of ['css/ilma.css','js/app.js','js/bank-services-ui.js','js/catalog-common.js','js/bank-ui.js','js/services-ui.js','js/account-ui.js','js/deposit-ui.js','js/loan-ui.js','fonts/fonts.css']) {
  const hash=require('node:crypto').createHash('sha256').update(fs.readFileSync('static/'+asset)).digest('hex').slice(0,16);
  assert.ok(html.includes('/static/'+asset+'?v=sha256-'+hash),'Asset URL must match current bytes: '+asset);
  assert.ok(fs.readFileSync('static/sw.js','utf8').includes('/static/'+asset+'?v=sha256-'+hash),'Worker asset URL must match: '+asset);
}
assert.match(html, /id="home-tap-target" class="home-speak-button"/);
console.log('Home visibility and asset-version regressions passed');

assert.equal(run('greetingFrames.length'), 4);
assert.equal(run('greetingFrames.map(frame => frame.lang).join(",")'), 'bn,en,bn,en');
run('showGreetingFrame(greetingFrames[2])');
assert.equal(element('home-greeting-line').textContent, 'ইস্টার্ন ব্যাংক কেমন আছে?');
run('showGreetingFrame(greetingFrames[3])');
assert.equal(element('home-greeting-line').textContent, 'How is Eastern Bank doing?');
run('currentLang = "bn"; stopGreetingCycle()');
assert.equal(element('home-greeting-line').textContent, run('T.bn.homeIdle'));
assert.ok(!html.includes('id="home-example"'));
console.log('Bilingual greeting regressions passed');

const css = fs.readFileSync('static/css/ilma.css', 'utf8');
assert.ok(css.includes(':is(#tab-services, #tab-detail, #tab-news)'), 'unified dark theme scope missing');
assert.ok(css.includes('--ink: var(--on-stage)'), 'unified dark theme ink missing');
const appSrc = fs.readFileSync('static/js/app.js', 'utf8');
assert.ok(appSrc.includes('var(--good-on-stage)'), 'calculator results must use on-stage tokens');
assert.ok(appSrc.includes('background: var(--paper)'), 'news cards must follow the tab theme');
assert.ok(!appSrc.includes('background: #FFF'), 'no white cards on the dark tabs');
assert.ok(!appSrc.includes('color: #555') && !appSrc.includes('color: #666'), 'no dark-grey notes on the dark tabs');
console.log('Unified Home theme regressions passed');

const servicesSrc = fs.readFileSync('static/js/services-ui.js', 'utf8');
assert.ok(servicesSrc.includes("back('services-home-back'"), 'services landing must offer a Home back button');
assert.ok(servicesSrc.includes("switchTab('home')"), 'services back button must return home');
assert.ok(servicesSrc.includes('tile-icon'), 'category tiles must use the icon badge');
assert.ok(servicesSrc.includes('tile-go'), 'category tiles must carry a tap hint');
assert.ok(css.includes('.catalog-tile .tile-icon'), 'tile badge styles missing');
assert.ok(css.includes('#tab-services .screen-header'), 'compact services header missing');
assert.ok(css.includes('.catalog-back .back-arrow'), 'prominent back-arrow badge style missing');
assert.ok(servicesSrc.includes('serviceSuggestions'), 'service suggestion shortcuts must be defined');
assert.ok(servicesSrc.includes('openComparison(s.target,s.calc)'), 'suggestion clicks must route to comparisons directly without voice clarification modal');
assert.ok(servicesSrc.includes('data-suggestion-index'), 'suggestion elements must bind by index');
const navSrc = fs.readFileSync('static/js/navigation.js', 'utf8');
assert.ok(navSrc.includes("event.target.closest('#services-home-back')"), 'services-home-back must not be intercepted by generic history.back()');
console.log('Services landing regressions passed: back button, tile design, compact header, direct suggestion comparison routing, prominent pill back button, home navigation isolation');

const depositSrc = fs.readFileSync('static/js/deposit-ui.js', 'utf8');
assert.ok(depositSrc.includes('deposit-group-card'), 'deposit view must use grouped cards');
assert.ok(depositSrc.includes('deposit-audience-select'), 'audience selection must use select dropdown');
assert.ok(depositSrc.includes('deposit-term-select'), 'term selection must use select dropdown');
assert.ok(depositSrc.includes('segmented-control'), 'product type and sorting must use segmented controls');
assert.ok(depositSrc.includes('deposit-section-heading'), 'all bank offers section heading must be present');
assert.ok(depositSrc.includes('deposit-bank-count'), 'bank count indicator must be present');
assert.ok(css.includes('.deposit-group-card'), 'deposit-group-card css missing');
assert.ok(css.includes('.segmented-control'), 'segmented-control css missing');
assert.ok(css.includes('.deposit-stat-banner'), 'deposit-stat-banner css missing');
assert.ok(css.includes('#deposit-rows .card-tile'), 'upgraded bank card tile css missing');
assert.ok(depositSrc.includes('deposit-empty-guidance'), 'empty guidance card must be provided when no specialized products match');
assert.ok(depositSrc.includes('deposit-sort-note'), 'comparison sort explanation note must be present');
assert.ok(css.includes('.deposit-empty-guidance'), 'deposit-empty-guidance css missing');
const accountSrc = fs.readFileSync('static/js/account-ui.js', 'utf8');
assert.ok(accountSrc.includes("account_audience==='all'"), 'account maintenance must fall back to all audience when specialized maintenance is unstated');
assert.ok(accountSrc.includes('account-audience-select'), 'account audience selection must use select dropdown');
assert.ok(accountSrc.includes('account-earnings-box'), 'account stat earnings banner must be present');
assert.ok(accountSrc.includes('account-bank-count'), 'account bank count indicator must be present');
assert.ok(accountSrc.includes('deposit-empty-guidance'), 'account empty guidance must be present');
assert.ok(accountSrc.includes('account-sort-note'), 'account sort explanatory note must be present');
console.log('Deposit and account comparison screen regressions passed: grouped cards, select controls, segmented tabs, bank list heading, stat banner, empty guidance');

// Header/dock geometry and content scrolling are checked by check_app_frame.py.
const bootstrap = html.match(/<script id="text-size-bootstrap">([\s\S]*?)<\/script>/)[1];
for (const [saved, expected] of [[null,'14px'],['14','14px'],['16','16px'],['19','19px'],['22','22px'],['8','14px']]) {
  let applied;
  require('node:vm').runInNewContext(bootstrap, {localStorage:{getItem:()=>saved}, document:{documentElement:{style:{setProperty:(key,value)=>{assert.equal(key,'--fs');applied=value;}}}}});
  assert.equal(applied,expected);
}
assert.doesNotThrow(()=>require('node:vm').runInNewContext(bootstrap,{localStorage:{getItem:()=>{throw Error('blocked');}}}));
console.log('Text size bootstrap passed: supported values, default, invalid storage and blocked storage');

const workerHash=require('node:crypto').createHash('sha256').update(fs.readFileSync('static/sw.js')).digest('hex').slice(0,16);
assert.ok(html.includes('data-worker-version="'+workerHash+'"'),'Worker registration version must match worker bytes');

// Optional fixed-prompt capability: distinguish missing clips from working live speech.
(async () => {
  context.fetch = async () => ({ok: true, json: async () => ({available: false, clips: {}})});
  await run('loadFixedClips()');
  assert.equal(element('settings-fixed-audio').hidden, false);
  run('currentLang="en";updateFixedClipStatus()');
  assert.match(element('settings-fixed-audio').textContent, /Saved prompt audio/);
  assert.match(element('settings-fixed-audio').textContent, /Online speech may still/);
  assert.equal(run('Object.keys(fixedClips).length'), 0);
  context.fetch = async () => ({ok: true, json: async () => ({available: true, clips: {'en:hint': {url:'/static/audio/fixed/en-hint.opus',fallback_url:'/static/audio/fixed/en-hint.mp3',text:'Synthetic prompt'}}})});
  await run('loadFixedClips()');
  assert.equal(element('settings-fixed-audio').hidden, true);
  assert.equal(run('fixedClips["en:hint"].text'), 'Synthetic prompt');
  context.fetch = async () => ({ok: false});
  await run('loadFixedClips()');
  assert.equal(element('settings-fixed-audio').hidden, false);
  assert.equal(run('Object.keys(fixedClips).length'), 0, 'Never retain stale clips after a validation failure');
  console.log('Fixed prompt capability, localization and unavailable fallback passed');
})().catch(error => {console.error(error);process.exitCode=1;});

const playbackSource=fs.readFileSync('static/js/app.js','utf8');
const playStart=playbackSource.indexOf('function playVoiceAudio');
assert.ok(playbackSource.indexOf('IlmaMicrophone.release()',playStart)<playbackSource.indexOf('player.src = url',playStart),'iOS releases the microphone before an answer plays');
assert.equal((playbackSource.match(/appSettings\.micExplained&&!window\.IlmaMicrophone\?\.closesForPlayback\?\.\(\)/g)||[]).length,2,'Both barge-in monitors stay closed during iOS playback');
{
  const set=[];let suspended=0;const window={navigator:{audioSession:{set type(v){set.push(v)}}},document:{addEventListener(){}},URL:{},AudioContext:class{state='running';resume(){return Promise.resolve()}suspend(){suspended++;this.state='suspended';return Promise.resolve()}}};
  require('node:vm').runInNewContext(fs.readFileSync('static/js/audio-session.js','utf8'),{window,Uint8Array,DataView,Blob:class{},Promise,setTimeout});
  window.IlmaAudioSession.getContext();window.IlmaAudioSession.forPlayback();window.IlmaAudioSession.forRecording();
  assert.deepEqual(set,['playback','play-and-record']);assert.equal(suspended,1);
  const plain={document:{addEventListener(){}},navigator:{}};require('node:vm').runInNewContext(fs.readFileSync('static/js/audio-session.js','utf8'),{window:plain,Promise});
  assert.doesNotThrow(()=>plain.IlmaAudioSession.forPlayback(),'Browsers without audioSession are unaffected');
}
assert.ok(playbackSource.indexOf('forPlayback',playStart)<playbackSource.indexOf('player.src = url',playStart),'iOS names playback mode before the answer plays');
console.log('iOS playback regressions passed: microphone released first, no barge-in monitor');
