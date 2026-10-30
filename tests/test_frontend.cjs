// Runtime regressions without a browser; layout still needs device verification.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
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
for (const asset of ['css/ilma.css','js/app.js','js/bank-services-ui.js','js/catalog-common.js','js/bank-ui.js','js/services-ui.js','fonts/fonts.css']) {
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
