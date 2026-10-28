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
assert.equal(element('card-status-word').textContent, 'Not enough data');
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
assert.match(html, /ilma\.css\?v=voice-complete-20261028-38/);
assert.match(html, /app\.js\?v=voice-complete-20261028-38/);
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
