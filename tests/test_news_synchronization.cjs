const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const elements = new Map();
function makeElement(id) {
  return {
    id,
    textContent: '',
    _innerHTML: '',
    set innerHTML(val) {
      this._innerHTML = val;
      if (val === '') this.children = [];
    },
    get innerHTML() {
      return this._innerHTML;
    },
    value: '',
    style: {},
    dataset: {},
    attributes: {},
    children: [],
    hidden: false,
    classList: {
      _classes: new Set(),
      add(c) { this._classes.add(c); },
      remove(c) { this._classes.delete(c); },
      toggle(c, force) {
        if (force === undefined) {
          if (this._classes.has(c)) this._classes.delete(c); else this._classes.add(c);
        } else if (force) this._classes.add(c); else this._classes.delete(c);
      },
      contains(c) { return this._classes.has(c); }
    },
    setAttribute(k, v) { this.attributes[k] = String(v); },
    getAttribute(k) { return this.attributes[k] || null; },
    removeAttribute(k) { delete this.attributes[k]; },
    pause() {},
    play() { return Promise.resolve(); },
    load() {},
    addEventListener() {},
    querySelectorAll(sel) {
      const results = [];
      function scan(el) {
        for (const child of el.children || []) {
          if (sel.startsWith('.') && child.classList?.contains(sel.slice(1))) results.push(child);
          else if (sel.startsWith('#') && child.id === sel.slice(1)) results.push(child);
          else if (sel.includes('data-news-category') && child.dataset?.newsCategory) results.push(child);
          else if (sel.includes('data-news-bank') && child.dataset?.newsBank) results.push(child);
          else if (sel.includes('news-card-listen') && child.classList?.contains('news-card-listen')) results.push(child);
          scan(child);
        }
      }
      scan(this);
      return results;
    },
    querySelector(sel) { return this.querySelectorAll(sel)[0] || null; },
    appendChild(child) { this.children.push(child); return child; },
    after(el) {},
    focus() {}
  };
}

function element(id) {
  if (!elements.has(id)) elements.set(id, makeElement(id));
  return elements.get(id);
}

// Pre-create required elements
const requiredIds = [
  'news-feed', 'extra-news-sections', 'news-filter-title', 'news-search-input',
  'news-search-clear', 'news-category-label', 'news-bank-label', 'news-audio-note',
  'news-feed-heading', 'news-feed-sub', 'lbl-listen-news', 'count-all', 'count-rules',
  'count-warnings', 'count-press', 'count-bank-all', 'count-bank-bb', 'count-bank-brac',
  'count-bank-city', 'lbl-cat-all', 'lbl-cat-rules', 'lbl-cat-warnings', 'lbl-cat-press',
  'lbl-bank-all', 'lbl-bank-bb', 'lbl-bank-brac', 'lbl-bank-city', 'news-highlight-title',
  'news-highlight-meta', 'news-highlight-label', 'news-highlight-banner', 'news-total-count',
  'news-empty-message', 'btn-listen-news', 'news-bank-select', 'home-tap-target',
  'btn-stop-listening', 'card-status-word', 'card-status-mark', 'card-insurance-line',
  'ret-amt-input', 'ret-rate-input', 'ret-result-box', 'lang-btn', 'home-greeting-line',
  'srv-title', 'srv-subtitle', 'lbl-listen-srv', 'srv-ins-heading', 'srv-ins-desc',
  'srv-amt-label', 'srv-type-label', 'opt-bank', 'opt-nbfi', 'srv-ret-heading', 'srv-ret-desc',
  'lbl-listen-rpt', 'btn-watch-bank', 'ins-amt-input', 'ins-type-select'
];
requiredIds.forEach(id => element(id));

const allDocElements = [];
function createCatBtn(cat) {
  const btn = makeElement('btn-cat-' + cat);
  btn.dataset.newsCategory = cat;
  btn.setAttribute('data-news-category', cat);
  btn.setAttribute('aria-pressed', cat === 'all' ? 'true' : 'false');
  allDocElements.push(btn);
  return btn;
}
function createBankBtn(bank) {
  const btn = makeElement('btn-bank-' + bank);
  btn.dataset.newsBank = bank;
  btn.setAttribute('data-news-bank', bank);
  btn.setAttribute('aria-pressed', bank === 'all' ? 'true' : 'false');
  allDocElements.push(btn);
  return btn;
}

const catButtons = ['all', 'rules', 'warnings', 'press'].map(createCatBtn);
const bankButtons = ['all', 'bb', 'brac', 'city'].map(createBankBtn);

const doc = {
  body: { style: {} },
  getElementById: (id) => element(id),
  querySelector: (sel) => {
    if (sel.startsWith('#')) return element(sel.slice(1));
    return allDocElements.find(e => e.dataset?.newsCategory || e.dataset?.newsBank) || makeElement('mock');
  },
  querySelectorAll: (sel) => {
    if (sel.includes('[data-news-category]')) return catButtons;
    if (sel.includes('[data-news-bank]')) return bankButtons;
    if (sel.includes('.news-card-listen')) {
      const res = [];
      const feed = element('news-feed');
      const extra = element('extra-news-sections');
      res.push(...feed.querySelectorAll('.news-card-listen'));
      res.push(...extra.querySelectorAll('.news-card-listen'));
      return res;
    }
    return [];
  },
  createElement: (tag) => makeElement(tag + '-' + Math.random().toString(36).slice(2, 7)),
  addEventListener: () => {},
  documentElement: { lang: 'bn' }
};

const context = vm.createContext({
  document: doc,
  window: { scrollTo() {}, speechSynthesis: { speak() {}, cancel() {}, speaking: false } },
  Audio: class MockAudio {
    constructor(src) { this.src = src; }
    play() { return Promise.resolve(); }
    pause() {}
  },
  SpeechSynthesisUtterance: class MockUtterance {
    constructor(text) { this.text = text; }
  },
  navigator: {},
  console,
  setTimeout: (fn) => { fn(); return 1; },
  clearTimeout() {},
  clearInterval() {},
  setInterval: () => 1
});

vm.runInContext(fs.readFileSync('static/js/app.js', 'utf8'), context);
function run(code) { return vm.runInContext(code, context); }

// Test 1: NEWS_SUMMARIES dictionary verification
const summaries = run('NEWS_SUMMARIES');
assert.ok(summaries, 'NEWS_SUMMARIES must exist');
assert.equal(typeof summaries['export-news-16-14'].bn, 'string');
assert.equal(typeof summaries['export-news-16-14'].en, 'string');
assert.equal(typeof summaries['extra54-rule-13'].bn, 'string');
assert.equal(typeof summaries['extra54-press-21'].bn, 'string');
assert.ok(summaries['export-news-16-14'].bn.includes('সিটি ব্যাংক'));
assert.ok(summaries['export-news-16-14'].en.includes('City Bank'));

// Seed sample news data
run(`
newsState.items = [
  { id: 'export-news-2-11', institution_id: 11, title_en: 'BRAC and City Bank launch new service, what does Digibox offer', title_bn: 'ব্র্যাক ও সিটি ব্যাংক চালু করল ডিজিবক্স', date: '2026-08-01', official: false },
  { id: 'export-news-12-11', institution_id: 11, title_en: 'BRAC Bank to issue Tk 1,000 crore green bond', title_bn: 'ব্র্যাক ব্যাংক ১,০০০ কোটি টাকার গ্রিন বন্ড ছাড়ছে', date: '2026-08-10', official: false },
  { id: 'export-news-13-11', institution_id: 11, title_en: "BRAC Bank's profit surges 57% in Jan-June 2026", title_bn: 'ব্র্যাক ব্যাংকের মুনাফা ৫৭ শতাংশ বেড়েছে', date: '2026-08-15', official: false },
  { id: 'export-news-16-14', institution_id: 14, title_en: 'City Bank plans to raise authorised capital to Tk 3,000 crore', title_bn: 'সিটি ব্যাংক মূলধন ৩,০০০ কোটি টাকায় উন্নীত করবে', date: '2026-08-20', official: false }
];
newsState.extra = {
  rules: [
    { item_id: 'extra54-rule-13', topic: 'new_rule', title: 'BRPD-1 Circular Letter No. 35', date: '2026-10-11', source_url: 'https://bb.org.bd' },
    { item_id: 'extra54-rule-19', topic: 'new_rule', title: 'BRPD-1 Circular Letter No. 34', date: '2026-10-01', source_url: 'https://bb.org.bd' }
  ],
  warnings: [
    { item_id: 'extra54-press-21', topic: 'bb_notice', title: 'Disruptions in Digital Transaction of Few Banks', date: '2026-10-06', source_url: 'https://bb.org.bd' }
  ],
  announcements: []
};
renderNews();
`);

// Test 2: City Bank isolation (City Bank MUST NOT display BRAC content)
run("setNewsBank('city')");
assert.equal(run("newsState.bank"), 'city', "newsState.bank must be 'city'");
assert.equal(run("newsState.category"), 'all', "newsState.category must remain 'all' (orthogonal)");
const cityBankBtn = bankButtons.find(b => b.dataset.newsBank === 'city');
assert.equal(cityBankBtn.getAttribute('aria-pressed'), 'true', "City Bank button must have aria-pressed='true'");

// Check rendered feed for City Bank
const feed = element('news-feed');
const cityCards = feed.children;
assert.equal(cityCards.length, 1, 'Only 1 card should be displayed for City Bank');
assert.ok(cityCards[0].innerHTML.includes('সিটি ব্যাংক মূলধন ৩,০০০ কোটি'), 'Must be City Bank authorized capital story');
assert.ok(!cityCards[0].innerHTML.includes('ব্র্যাক ও সিটি ব্যাংক'), 'BRAC Digibox story must NOT be in City Bank feed');
assert.ok(!cityCards[0].innerHTML.includes('export-news-2-11'), 'BRAC item id must NOT be present');
console.log('City Bank isolation passed: BRAC content strictly excluded');

// Test 3: Selection synchronization (Orthogonal, independent tab rows)
run("setNewsCategory('press')");
assert.equal(run("newsState.category"), 'press', "category must be 'press'");
assert.equal(run("newsState.bank"), 'city', "bank must still be 'city'!");

// Switch bank to BRAC
run("setNewsBank('brac')");
assert.equal(run("newsState.bank"), 'brac', "bank must be 'brac'");
assert.equal(run("newsState.category"), 'press', "category must still be 'press'!");
assert.equal(feed.children.length, 3, 'BRAC Bank press should show 3 items');

// Switch category to rules (BRAC has 0 direct rules -> empty guidance with switch buttons)
run("setNewsCategory('rules')");
assert.equal(run("newsState.category"), 'rules', "category must stay 'rules'");
assert.equal(run("newsState.bank"), 'brac', "bank must stay 'brac'");
const emptyMsg = element('news-empty-message');
assert.equal(emptyMsg.hidden, false, 'Empty guidance should be visible when BRAC has 0 rules');
assert.ok(emptyMsg.innerHTML.includes('ব্র্যাক ব্যাংক'), 'Guidance mentions BRAC Bank');
assert.ok(emptyMsg.innerHTML.includes('guidance-switch-cat'), 'Guidance includes quick-switch button');
console.log('Category and bank orthogonal synchronization passed');

// Test 4: Audio summary integration on news cards
run("setNewsCategory('all')");
run("setNewsBank('all')");
const allPressCards = feed.children;
assert.equal(allPressCards.length, 4, 'All press items should render');
for (const card of allPressCards) {
  assert.ok(card.innerHTML.includes('news-summary-box'), 'Each card must have news-summary-box');
  assert.ok(card.innerHTML.includes('news-card-listen'), 'Each card must have news-card-listen button');
}

// Test per-card audio play & stop toggle
const testBtn = makeElement('btn-listen-test');
testBtn.dataset.newsAudio = 'export-news-16-14';
const mockLabel = makeElement('label');
mockLabel.classList.add('listen-label');
testBtn.children.push(mockLabel);
testBtn.querySelector = (sel) => sel.includes('listen-label') ? mockLabel : null;
context.testBtn = testBtn;

run("playNewsSummary('export-news-16-14', testBtn)");
assert.ok(testBtn.classList.contains('is-playing'), 'Button must have is-playing class');
assert.equal(mockLabel.textContent, 'থামুন', 'Playing label must say থামুন');

// Second click stops audio
run("playNewsSummary('export-news-16-14', testBtn)");
assert.ok(!testBtn.classList.contains('is-playing'), 'Button must remove is-playing class on stop');
assert.equal(mockLabel.textContent, 'সারসংক্ষেপ শুনুন', 'Idle label must say সারসংক্ষেপ শুনুন');

console.log('Per-card audio summary playback & toggle passed');
console.log('All news synchronization & audio tests PASSED successfully!');
