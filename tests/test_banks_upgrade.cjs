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
    },
    get innerHTML() {
      return this._innerHTML;
    },
    value: '',
    style: {},
    dataset: {},
    attributes: {},
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
    getAttribute(k) { return this.attributes[k] ?? null; },
    focus() {},
    querySelectorAll(selector) {
      return [];
    },
    replaceChildren() {
      this.innerHTML = '';
      this.textContent = '';
    }
  };
}

function getElement(id) {
  if (!elements.has(id)) {
    elements.set(id, makeElement(id));
  }
  return elements.get(id);
}

const context = vm.createContext({
  document: {
    getElementById: getElement,
    querySelector: getElement,
    querySelectorAll: () => [],
    addEventListener: () => {},
    body: { style: {} },
    documentElement: {}
  },
  window: {
    scrollTo: () => {},
    addEventListener: () => {},
    IlmaMicrophone: { release: () => {}, closesForPlayback: () => false },
    IlmaAudioSession: { unlock: () => {} },
    IlmaNavigation: { visit: () => {} },
    IlmaServices: { openBankServices: () => {}, openComparison: () => {}, enter: () => {}, relocalize: () => {}, listenLabel: () => 'Listen' }
  },
  navigator: {},
  console,
  setTimeout: fn => { fn(); return 1; },
  clearTimeout: () => {},
  fetch: async () => ({ ok: false })
});

// Load common and bank scripts
vm.runInContext(fs.readFileSync('static/js/app.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('static/js/catalog-common.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('static/js/bank-ui.js', 'utf8'), context);

function run(code) {
  return vm.runInContext(code, context);
}

// 11 demo banks dataset
const demoBanks = [
  { id: 19, slug: 'ebl', name_bn: 'ইস্টার্ন ব্যাংক পিএলসি', name_en: 'Eastern Bank PLC', aliases: ['ebl'], listed: true, status: { code: 'strong' } },
  { id: 7, slug: 'bracbank', name_bn: 'ব্র্যাক ব্যাংক পিএলসি', name_en: 'BRAC Bank PLC', aliases: ['brac'], listed: true, status: { code: 'strong' } },
  { id: 11, slug: 'citybank', name_bn: 'সিটি ব্যাংক পিএলসি', name_en: 'City Bank PLC', aliases: ['city'], listed: true, status: { code: 'strong' } },
  { id: 18, slug: 'dutchbangl', name_bn: 'ডাচ্-বাংলা ব্যাংক পিএলসি', name_en: 'Dutch-Bangla Bank PLC', aliases: ['dbbl'], listed: true, status: { code: 'strong' } },
  { id: 6, slug: 'bankasia', name_bn: 'ব্যাংক এশিয়া পিএলসি', name_en: 'Bank Asia PLC', aliases: ['asia'], listed: true, status: { code: 'strong' } },
  { id: 24, slug: 'islamibank', name_bn: 'ইসলামী ব্যাংক বাংলাদেশ পিএলসি', name_en: 'Islami Bank Bangladesh PLC', aliases: ['ibbl'], islamic: true, listed: true, status: { code: 'high' } },
  { id: 31, slug: 'mtb', name_bn: 'মিউচুয়াল ট্রাস্ট ব্যাংক পিএলসি', name_en: 'Mutual Trust Bank PLC', aliases: ['mtb'], listed: true, status: { code: 'strong' } },
  { id: 34, slug: 'nbl', name_bn: 'ন্যাশনাল ব্যাংক লিমিটেড', name_en: 'National Bank Limited', aliases: ['nbl'], listed: true, status: { code: 'high' } },
  { id: 35, slug: 'nccbank', name_bn: 'এনসিসি ব্যাংক পিএলসি', name_en: 'NCC Bank PLC', aliases: ['ncc'], listed: true, status: { code: 'strong' } },
  { id: 39, slug: 'primebank', name_bn: 'প্রাইম ব্যাংক পিএলসি', name_en: 'Prime Bank PLC', aliases: ['prime'], listed: true, status: { code: 'strong' } },
  { id: 48, slug: 'sbacbank', name_bn: 'সাউথ বাংলা এগ্রিকালচারাল অ্যান্ড কমার্স ব্যাংক পিএলসি', name_en: 'South Bangla Agriculture and Commerce Bank PLC', aliases: ['sbac'], listed: true, status: { code: 'no_data' } }
];

// Test 1: Bank list view rendering and sector totals
run(`window.IlmaBank.setBanks(${JSON.stringify(demoBanks)}); currentLang = 'bn';`);
run(`window.IlmaBank.renderBankList()`);
const listViewHtml = getElement('bank-list-view').innerHTML;

assert.ok(listViewHtml.includes('bank-sector-overview'), 'Sector overview bar must be rendered');
assert.ok(listViewHtml.includes('১১'), 'Total 11 banks must be present in sector overview');
assert.ok(listViewHtml.includes('৮'), '8 low risk banks count must be present');
assert.ok(listViewHtml.includes('২'), '2 high risk banks count must be present');
assert.ok(listViewHtml.includes('১'), '1 unrated bank count must be present');
assert.ok(listViewHtml.includes('data-type-filter="all"'), 'Type filter tabs must be present');
assert.ok(listViewHtml.includes('data-type-filter="islamic"'), 'Islamic filter tab must be present');
assert.ok(listViewHtml.includes('data-risk-filter="strong"'), 'Strong risk filter tab must be present');

const rowsHtml = getElement('bank-list-rows').innerHTML;
assert.ok(rowsHtml.includes('data-bank="19"'), 'EBL card must be present');
assert.ok(rowsHtml.includes('bank-avatar'), 'Monogram avatar must be present');
assert.ok(rowsHtml.includes('EBL'), 'EBL monogram text must be present');
assert.ok(rowsHtml.includes('BRAC'), 'BRAC monogram text must be present');
assert.ok(rowsHtml.includes('CITY'), 'CITY monogram text must be present');
assert.ok(rowsHtml.includes('IBBL'), 'IBBL monogram text must be present');
assert.ok(rowsHtml.includes('SBAC'), 'SBAC monogram text must be present');

// Test 2: In English mode, [data-bank="19"] must NOT contain <small> (check_website_review regression)
run(`currentLang = 'en'; window.IlmaBank.renderBankList()`);
const rowsEn = getElement('bank-list-rows').innerHTML;
const eblMatch = rowsEn.match(/<button[^>]*data-bank="19"[^>]*>([\s\S]*?)<\/button>/);
assert.ok(eblMatch, 'EBL button must exist in English mode');
assert.ok(!eblMatch[1].includes('<small'), 'In English mode, bank card must NOT contain any <small> tag');
assert.ok(eblMatch[1].includes('Eastern Bank PLC'), 'English name must be rendered');
assert.ok(eblMatch[1].includes('EBL'), 'EBL monogram must be present');

// Test 3: Sourced Report Card for EBL (CRAR 15.49%, NPL 2.24%, Insurance 2 Lakh)
const eblReport = {
  institution: { id: 19, slug: 'ebl', name_bn: 'ইস্টার্ন ব্যাংক পিএলসি', name_en: 'Eastern Bank PLC', islamic: false },
  status: { code: 'strong', label_bn: 'ঝুঁকি কম', label_en: 'Low risk' },
  figures: [
    { metric: 'crar', value: 0.1549, period: '2023', basis: 'audited' },
    { metric: 'npl_ratio', value: 0.0224, period: '2023', basis: 'audited' },
    { metric: 'net_profit', value: 6118000000, period: '2023', basis: 'audited' }
  ],
  insurance: {
    covered: true,
    limit_bdt: 200000,
    text_bn: 'আমানত সুরক্ষা ২ লাখ টাকা পর্যন্ত',
    text_en: 'Deposit protection up to 2 lakh BDT',
    source_url: 'https://bb.org.bd/law'
  },
  reasons: [
    { rule: 'C1', text_bn: 'মূলধন অনুপাত ১৫.৪৯% যা আইনি সীমা ১০% এর বেশি।', text_en: 'CRAR is 15.49%, exceeding 10% legal rule.', source_title: 'Annual Report 2023' }
  ],
  section_counts: { health: 1, rating: 1, services: 1, history: 0, news: 2 }
};

run(`currentLang = 'bn'; window.IlmaBank.reportReady(${JSON.stringify(eblReport)})`);
const kpiBn = getElement('bank-kpi-summary').innerHTML;
assert.ok(kpiBn.includes('১৫.৪৯%'), 'EBL CRAR 15.49% must be displayed');
assert.ok(kpiBn.includes('২.২৪%'), 'EBL NPL 2.24% must be displayed');
assert.ok(kpiBn.includes('২ লাখ ৳'), 'EBL deposit insurance 2 lakh BDT must be displayed');
assert.ok(kpiBn.includes('আইনি সীমা ≥ ১০% পূরণ ✓'), 'Benchmark compliance badge must be displayed');
assert.ok(kpiBn.includes('স্বাভাবিক সীমা (≤ ৫%) ✓'), 'NPL tolerable range badge must be displayed');

// Test 4: Missing Figures Bank (SBAC - Zero hallucination, must show "অপ্রকাশিত / Not published")
const sbacReport = {
  institution: { id: 48, slug: 'sbacbank', name_bn: 'সাউথ বাংলা এগ্রিকালচারাল অ্যান্ড কমার্স ব্যাংক পিএলসি', name_en: 'South Bangla Agriculture and Commerce Bank PLC', islamic: false },
  status: { code: 'no_data', label_bn: 'মূল্যায়ন করা হয়নি', label_en: 'Not rated' },
  figures: [],
  insurance: {
    covered: true,
    limit_bdt: 200000,
    text_bn: 'আমানত সুরক্ষা ২ লাখ টাকা পর্যন্ত',
    text_en: 'Deposit protection up to 2 lakh BDT',
    source_url: 'https://bb.org.bd/law'
  },
  reasons: [],
  section_counts: { health: 0, rating: 1, services: 1, history: 0, news: 0 }
};

run(`currentLang = 'bn'; window.IlmaBank.reportReady(${JSON.stringify(sbacReport)})`);
const kpiSbac = getElement('bank-kpi-summary').innerHTML;
assert.ok(kpiSbac.includes('অপ্রকাশিত'), 'Missing CRAR must be displayed as অপ্রকাশিত, never fabricated');
assert.ok(!kpiSbac.includes('NaN'), 'No NaN values in KPI display');

// Test 5: Section Navigation Tiles in #bank-detail-links
const linksHtml = getElement('bank-detail-links').innerHTML;
assert.ok(linksHtml.includes('bank-nav-tile'), 'Navigation buttons must use bank-nav-tile class');
assert.ok(linksHtml.includes('data-bank-detail="rating"'), 'Rating button must have data-bank-detail attribute');
assert.ok(linksHtml.includes('data-bank-detail="services"'), 'Services button must have data-bank-detail attribute');
assert.ok(linksHtml.includes('data-bank-detail="ask"'), 'Ask button must have data-bank-detail attribute');
assert.ok(linksHtml.includes('🛡️'), 'Rating icon must be present');
assert.ok(linksHtml.includes('💳'), 'Services icon must be present');
assert.ok(linksHtml.includes('💬'), 'Ask icon must be present');

// Test 6: Insurance line contains "2 lakh" and source link (check_website_review assertions)
run(`currentLang = 'en'; window.IlmaBank.reportReady(${JSON.stringify(eblReport)})`);
const insLine = getElement('card-insurance-line').innerHTML;
assert.ok(insLine.includes('2 lakh'), 'Insurance line must contain 2 lakh in English mode');
assert.ok(insLine.includes('<a class="catalog-source"'), 'Insurance line must contain direct <a> link for tests');

console.log('All Banks tab upgrade tests PASSED successfully!');
