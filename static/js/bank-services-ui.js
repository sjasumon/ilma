/* Bank and service screens. Personal calculator inputs never enter a request. */
(() => {
  const $ = id => document.getElementById(id), E = escapeHTML;
  const tr = (bn,en) => currentLang === 'bn' ? bn : en;
  const digits = value => currentLang === 'bn' ? toBnDigits(value) : String(value);
  const dateText = value => value ? new Intl.DateTimeFormat(currentLang==='bn'?'bn-BD':'en-GB',{day:'numeric',month:'long',year:'numeric'}).format(new Date(String(value).slice(0,10)+'T00:00:00')) : '—';
  const number = value => digits(Number(value).toLocaleString('en-IN',{maximumFractionDigits:2}));
  let banks=[], categories=[], bankPage='list', detailKind='health', servicePage='home', bankFilter=null;
  let choice={product_type:'fdr',tenor_months:12,basis:'conventional'}, comparison=null, bankOffers=null, offerDetail=null, epoch=0;
  let calculatorPrefill={};
  let serviceManifest={clips:{}};
  function loadServiceManifest(){return fetch('/v1/services/audio-manifest',{cache:'no-store'}).then(response=>response.ok?response.json():{clips:{}}).then(data=>{serviceManifest=data;}).catch(()=>{});}
  const labels={fdr:['এফডিআর','FDR'],dps:['ডিপিএস','DPS'],savings:['সঞ্চয়ী হিসাব','Savings'],card:['কার্ড','Card'],
    home_loan:['গৃহঋণ','Home loan'],auto_loan:['গাড়ির ঋণ','Auto loan'],personal_loan:['ব্যক্তিগত ঋণ','Personal loan'],
    loan_against_fdr:['এফডিআরের বিপরীতে ঋণ','Loan against FDR'],account_fee:['অ্যাকাউন্ট','Accounts'],
    annual_fee:['বার্ষিক ফি','Annual fee'],renewal_fee:['নবায়ন ফি','Renewal fee'],interest_rate:['সুদের হার','Interest rate'],
    rate:['বার্ষিক হার','Annual rate'],rate_min:['সর্বনিম্ন হার','Minimum rate'],rate_max:['সর্বোচ্চ হার','Maximum rate'],
    maintenance_fee_half_yearly:['অর্ধবার্ষিক রক্ষণাবেক্ষণ','Half-yearly maintenance'],late_fee:['বিলম্ব ফি','Late fee'],
    foreign_currency_markup:['বৈদেশিক মুদ্রা মার্কআপ','Foreign currency markup'],processing_fee:['প্রক্রিয়াকরণ ফি','Processing fee'],
    closing_fee:['বন্ধের ফি','Closing fee'],sms_alert_fee:['এসএমএস ফি','SMS fee'],cheque_book_fee:['চেকবই ফি','Cheque book fee']};
  Object.assign(labels,{
    card_replacement_fee:['কার্ড প্রতিস্থাপন ফি','Card replacement fee'],cash_advance_fee:['নগদ অগ্রিম ফি','Cash advance fee'],
    supplementary_card_fee:['অতিরিক্ত কার্ডের ফি','Supplementary card fee'],lounge_access:['লাউঞ্জ সুবিধা','Lounge access'],
    fee_waiver_rule:['ফি মওকুফের শর্ত','Fee waiver rule'],early_settlement_fee:['আগে ঋণ পরিশোধের ফি','Early settlement fee'],
    partial_payment_fee:['আংশিক পরিশোধের ফি','Partial payment fee'],minimum_balance:['ন্যূনতম স্থিতি','Minimum balance'],
    min_monthly_installment:['ন্যূনতম মাসিক কিস্তি','Minimum monthly installment'],atm_other_bank_fee:['অন্য ব্যাংকের এটিএম ফি','Other-bank ATM fee']
  });
  const label = key => labels[key]?.[currentLang==='bn'?0:1] || key.replaceAll('_',' ');
  const outlooks={stable:['স্থির','Stable'],positive:['ইতিবাচক','Positive'],negative:['নেতিবাচক','Negative'],developing:['অনিশ্চিত','Developing (uncertain)']};
  const outlook = value => outlooks[value]?.[currentLang==='bn'?0:1] || value || '—';
  const percent = value => digits(Number(value).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}));
  const bankName = bank => currentLang==='bn'?bank.name_bn:bank.name_en;
  const statusChip = bank => `<span class="catalog-status ${E(bank.status?.code||'no_data')}">${({strong:'✓',watch:'⚠',high:'✕',no_data:'?'})[bank.status?.code||'no_data']} ${E(currentLang==='bn'?bank.status?.label_bn:bank.status?.label_en)}</span>`;
  const bankNames = bank => `<strong>${E(bankName(bank))}</strong>${currentLang==='bn'?`<small lang="en">${E(bank.name_en)}</small>`:''}`;
  const productText = row => row.product_type==='card'?(currentLang==='bn'?row.card_display_bn:row.card_display_en):currentLang==='en'?row.product:[label(row.product_type||choice.product_type),row.tenor_months?`${digits(row.tenor_months)} মাস`:''].filter(Boolean).join(' · ');
  function conditionText(row) {
    if(row.product_type==='card')return currentLang==='bn'?(row.condition_bn||''):(row.condition_en||'');
    if(currentLang==='en')return row.condition;
    if(!row.condition)return '';
    const text=row.condition.trim().replace(/^\d+\s+months?\s+/i,'');
    const match=text.match(/^(?:amount\s+)?(?:less\s+than|below|under)\s*(?:bdt|tk\.?)?\s*([\d.,]+)\s*(crore|lac|lakh|million)?\.?$/i);
    if(match)return `${digits(match[1])} ${{crore:'কোটি',lac:'লাখ',lakh:'লাখ',million:'মিলিয়ন'}[match[2]?.toLowerCase()]||''} টাকার কম`;
    const vat=text.match(/(\d+(?:\.\d+)?)\s*%\s*VAT/i);
    if(vat)return `${digits(vat[1])}% ভ্যাট প্রযোজ্য। অন্যান্য শর্ত মূল সূত্রে দেখুন।`;
    return 'বিশেষ শর্ত প্রযোজ্য। মূল সূত্রে বিস্তারিত দেখুন।';
  }
  const offerStatus = bank => bank.status?.code==='no_data'?`<p class="catalog-unverified" role="note">${tr('ব্যাংকের অবস্থা যাচাই হয়নি — বেশি হার মানেই ঝুঁকি কম নয়।','Bank condition is unverified — a higher rate does not mean lower risk.')}</p>`:statusChip(bank);
  const empty = text => `<p class="catalog-empty" role="status">${E(text||tr('এই তথ্য আমাদের কাছে নেই।','We do not have this information.'))}</p>`;
  const back = (id,text) => `<button type="button" class="catalog-back" id="${id}">← ${E(text)}</button>`;
  async function json(url) {
    const response=await fetch(url);
    if(!response.ok) throw Error(tr('তথ্য লোড করা যায়নি। আবার চেষ্টা করুন।','Could not load data. Please try again.'));
    const data=await response.json();
    if(response.headers?.get('X-ILMA-Offline')==='1')data._offline=true;
    return data;
  }
  function sourceButton(source,bank=null) {
    const subject=currentLang==='bn'?(source.product?productText(source):({crar:'মূলধন অনুপাত',npl_ratio:'খেলাপি ঋণ',net_profit:'মুনাফা'})[source.metric]||'মূল নথি'):(source.product||source.source_title||source.metric||'');
    return `<button class="catalog-source" type="button" aria-label="${E(tr('সূত্র দেখুন: ','Show source: ')+(bank?bankName(bank)+' · ':'')+subject)}" data-source="${E(source.fact_id||source.offer_id||'')}">${tr('সূত্র ›','Source ›')}${source.checked?' ✓':''}</button>`;
  }
  function wireSources(root,rows) {
    root.querySelectorAll('[data-source]').forEach(button => button.addEventListener('click',()=>{
      const row=rows.find(row=>(row.fact_id||row.offer_id||'')===button.dataset.source);
      if(row)openProofModal(row.source_title||row.product,row.quote,row.source_url,row.page,row.published_at||row.doc_date,
        row.metric==='net_profit'?tr('পরিমাণ কোটি টাকায় দেখানো হয়েছে। মূল একক সূত্রে দেখুন।','Amounts are displayed in crore BDT. See the source for original units.'):(row.condition||''));
    }));
  }
  function voice(tab,bank=null) { switchTab('home'); activeVoiceContext={tab,bank_id:bank}; startListening(); }
  function ask(text,tab,bank=null) { activeVoiceContext={tab,bank_id:bank}; return submitTextQuestion(text); }
  function error(root,error) { root.innerHTML=empty(error.message)+`<button type="button" class="catalog-action" data-retry>${tr('আবার চেষ্টা করুন','Try again')}</button>`;root.querySelector('[data-retry]').onclick=()=>window.IlmaCatalog.enter(currentTab); }
  function reportView(show) {
    $('main-content').scrollTop=0;
    $('bank-list-view').hidden=show;
    $('bank-report-view').hidden=!show;
    $('bank-detail-view').hidden=true;
  }
  async function showBankList() {
    ++reportRequest; reportCardData=null;bankPage='list'; currentBankId=null; reportView(false); $('bank-list-view').hidden=false;
    const root=$('bank-list-view'), request=++epoch;
    root.innerHTML=empty(tr('একটু অপেক্ষা করুন…','Please wait…'));
    try { banks=await json('/v1/institutions?list=demo'); if(request!==epoch)return; renderBankList(); }
    catch(e){if(request===epoch)error(root,e);}
  }
  function renderBankList() {
    const root=$('bank-list-view');
    root.innerHTML=`<div class="screen-header"><h1>${tr('ব্যাংক','Banks')}</h1><p>${tr('কোন ব্যাংকের অবস্থা জানতে চান?','Which bank do you want to check?')}</p>
      <div class="catalog-search"><label class="sr-only" for="bank-list-search">${tr('ব্যাংকের নাম লিখুন','Type a bank name')}</label><input id="bank-list-search" type="search" placeholder="${tr('ব্যাংকের নাম লিখুন','Type a bank name')}"><button type="button" id="bank-list-mic" aria-label="${tr('ব্যাংকের নাম বলুন','Say a bank name')}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/></svg></button></div></div>
      <div class="sheet"><div id="bank-list-rows"></div><p class="catalog-note">${tr(`ডেমোতে ${digits(banks.length)}টি ব্যাংক আছে। আরও ব্যাংক শিগগির।`,`${banks.length} banks in the demo. More banks coming soon.`)}</p><button type="button" class="catalog-source" id="prior-work">${tr('তথ্য কোথা থেকে এসেছে','Where the data comes from')}</button></div>`;
    function rows(){const query=$('bank-list-search').value.trim().toLowerCase();
      $('bank-list-rows').innerHTML=banks.filter(b=>`${b.name_bn} ${b.name_en} ${b.slug} ${(b.aliases||[]).join(" ")}`.toLowerCase().includes(query)).sort((a,b)=>a.name_bn.localeCompare(b.name_bn,'bn')).map(bank=>
        `<button class="catalog-bank-row" type="button" data-bank="${bank.id}"><span>${bankNames(bank)}</span>${statusChip(bank)}</button>`).join('')||empty();
      root.querySelectorAll('[data-bank]').forEach(button=>button.onclick=()=>openBank(Number(button.dataset.bank)));
    }
    rows(); $('bank-list-search').oninput=rows; $('bank-list-mic').onclick=()=>voice('bank');
    $('prior-work').onclick=()=>openProofModal(tr('তথ্য কোথা থেকে এসেছে','Where the data comes from'),tr(
      'তথ্য সুমনের দেওয়া v5.2 ও v6.2 রপ্তানি থেকে এসেছে। ILMA-র কোড আলাদাভাবে তৈরি। agent-v4, agent-v5 ও agent-v6.2 চিহ্নিত তথ্য সুমনের হাতে যাচাই করা নয়। ঘটনার তালিকা সম্পূর্ণ নয়; সংবাদকে সরকারি সিদ্ধান্ত হিসেবে দেখানো হয় না।',
      'Data comes from the v5.2 and v6.2 exports supplied by Sumon. ILMA code is implemented separately. Agent-v4, agent-v5 and agent-v6.2 rows have not been personally checked by Sumon. Incident coverage is incomplete; news reports are not treated as official findings.'),'',null,null);
  }
  function showReport() { ++epoch; bankPage='report';reportView(true);$('btn-watch-bank').setAttribute('aria-pressed','false');$('btn-watch-bank').disabled=true;loadReportCard(currentBankId); }
  function reportReady(data) {
    const bn=currentLang==='bn', bank=data.institution;
    $('bank-list-back').textContent='← '+tr('ব্যাংক','Banks');$('bank-list-back').onclick=showBankList;
    $('card-bank-meta').textContent=`${bn?bank.name_en+' · ':''}${tr('ব্যাংক','Bank')} · ${tr('তথ্যের তারিখ','Figures as of')}: ${dateText(data.data_date)} · ${tr('হালনাগাদ','Updated')}: ${dateText(data.updated_at)}${data._offline?tr(' · অফলাইন কপি',' · Offline copy'):''}`;
    $('card-insurance-line').textContent=(bn?data.insurance?.text_bn:data.insurance?.text_en)||tr('বীমার যাচাইকৃত সূত্র এখনও যোগ করা হয়নি।','A verified insurance source has not been loaded yet.');
    if(data.insurance?.source_url){const source=document.createElement('a');source.className='catalog-source';source.href=data.insurance.source_url;source.target='_blank';source.rel='noopener noreferrer';source.textContent=tr('আইনের সূত্র ↗','Legal source ↗');$('card-insurance-line').appendChild(document.createElement('br'));$('card-insurance-line').appendChild(source);}
    let watchNotice=$('watch-notice');if(!watchNotice){watchNotice=document.createElement('p');watchNotice.id='watch-notice';watchNotice.className='catalog-note';watchNotice.setAttribute('role','status');$('btn-watch-bank').parentElement.after(watchNotice);}
    watchNotice.textContent=tr('নজরে রাখলে শুধু তালিকায় সংরক্ষিত হবে। SMS/WhatsApp বিজ্ঞপ্তি শিগগির আসছে।','Watch saves this bank to your list. SMS/WhatsApp alerts are coming soon.');
    $('card-why-heading').textContent=tr('কেন?','Why?');
    $('bank-not-checked').textContent=bn?data.not_checked_bn:data.not_checked_en;
    $('bank-detail-links').innerHTML=[['health','আর্থিক অবস্থা','Financial health'],['rating','রেটিং','Rating'],['history','জালিয়াতি ও মামলার ইতিহাস','Fraud and legal history'],['news','খবর','News about this bank'],['announcements','কোম্পানির ঘোষণা','Company announcements'],['reports','প্রতিবেদন','Reports'],['bb-notices','এই ব্যাংক নিয়ে বাংলাদেশ ব্যাংকের নোটিশ','BB notices about this bank'],['services','এই ব্যাংকের সেবা ও হার','Services and rates'],['ask','এই ব্যাংক নিয়ে প্রশ্ন করুন','Ask about this bank']].map(([key,b,e])=>`<button type="button" class="catalog-detail-row" data-bank-detail="${key}">${tr(b,e)}${key==='history'?' ('+digits(data.incident_count||0)+')':''} <span aria-hidden="true">›</span></button>`).join('');
    $('bank-detail-links').querySelectorAll('button').forEach(button=>button.onclick=()=>button.dataset.bankDetail==='services'?openBankServices(bank.id):showBankDetail(button.dataset.bankDetail));
    $('btn-watch-bank').disabled=!anonymousDevice;
    if(anonymousDevice)fetch(`/v1/institutions/${bank.id}/watch`,{headers:{'X-ILMA-Device':anonymousDevice}}).then(r=>r.ok?r.json():null).then(state=>{if(state&&currentBankId===bank.id){$('btn-watch-bank').setAttribute('aria-pressed',String(state.watching));$('lbl-watch-rpt').textContent=state.watching?tr('নজরে রাখা হচ্ছে','Watching'):tr('নজরে রাখুন','Watch');}}).catch(()=>{});
  }
  async function toggleWatch(){
    if(!currentBankId||!anonymousDevice){$('sr-announcer').textContent=tr('এই ডিভাইসে নজরে রাখার পরিচয় তৈরি করা যায়নি।','Could not create a watch identifier on this device.');return;}
    const bank=currentBankId,button=$('btn-watch-bank');button.disabled=true;
    try{const response=await fetch(`/v1/institutions/${bank}/watch`,{method:button.getAttribute('aria-pressed')==='true'?'DELETE':'POST',headers:{'X-ILMA-Device':anonymousDevice}});
      if(!response.ok)throw Error();const state=await response.json();if(currentBankId!==bank)return;
      button.setAttribute('aria-pressed',String(state.watching));$('lbl-watch-rpt').textContent=state.watching?tr('নজরে রাখা হচ্ছে','Watching'):tr('নজরে রাখুন','Watch');
      $('sr-announcer').textContent=state.watching?tr('নজরে রাখার তালিকায় যোগ হয়েছে। বিজ্ঞপ্তি এখনও চালু নয়।','Added to your watch list. Notifications are not active yet.'):tr('নজরে রাখার তালিকা থেকে সরানো হয়েছে।','Removed from your watch list.');
      if($('watch-notice'))$('watch-notice').textContent=state.watching?tr('তালিকায় সংরক্ষিত। SMS/WhatsApp বিজ্ঞপ্তি শিগগির আসছে; এখন পাঠানো হবে না।','Saved to your list. SMS/WhatsApp alerts are coming soon; none will be sent now.'):tr('তালিকা থেকে সরানো হয়েছে। বিজ্ঞপ্তি এখনও চালু নয়।','Removed from the list. Alerts are not active yet.');
    }catch{$('sr-announcer').textContent=tr('নজরে রাখার পরিবর্তন সংরক্ষণ করা যায়নি।','Could not save the watch change.');}finally{button.disabled=false;}
  }
  async function showBankDetail(kind) {
    $('main-content').scrollTop=0;
    bankPage='detail';detailKind=kind;const root=$('bank-detail-view'), request=++epoch;
    $('bank-list-view').hidden=true;$('bank-report-view').hidden=true;root.hidden=false;
    const titles={health:tr('আর্থিক অবস্থা','Financial health'),rating:tr('রেটিং','Rating'),news:tr('খবর','News'),history:tr('জালিয়াতি ও মামলার ইতিহাস','Fraud and legal history'),ask:tr('এই ব্যাংক নিয়ে প্রশ্ন করুন','Ask about this bank')};
    root.innerHTML=`<div class="screen-header">${back('bank-detail-back',tr('রিপোর্ট কার্ড','Report card'))}<h1>${E(titles[kind])}</h1><p>${E(reportCardData?bankName(reportCardData.institution):'')}</p></div><div class="sheet" id="bank-detail-body">${empty(tr('একটু অপেক্ষা করুন…','Please wait…'))}</div>`;
    $('bank-detail-back').onclick=showReport;const body=$('bank-detail-body');
    if(kind==='ask') {
      body.innerHTML=`<form id="bank-ask-form"><label for="bank-ask-text">${tr('আপনার প্রশ্ন','Your question')}</label><input class="calc-field" id="bank-ask-text" maxlength="1000" required><button class="catalog-action" type="submit">${tr('খুঁজুন','Ask')}</button></form><button class="catalog-action" id="bank-detail-mic" type="button">${tr('প্রশ্ন বলুন','Ask by voice')}</button><div class="catalog-suggestions">${[
        ['এই ব্যাংকের খেলাপি ঋণ কত?','What are this bank’s bad loans?'],['রেটিং কী?','What is the rating?'],['আমার টাকা কতটা সুরক্ষিত?','How much of my deposit is insured?']].map(([b,e])=>`<button class="catalog-detail-row" type="button" data-suggestion="${E(tr(b,e))}">${E(tr(b,e))}</button>`).join('')}</div>`;
      $('bank-ask-form').onsubmit=e=>{e.preventDefault();ask($('bank-ask-text').value,'bank',currentBankId);};
      $('bank-detail-mic').onclick=()=>voice('bank',currentBankId);
      body.querySelectorAll('[data-suggestion]').forEach(b=>b.onclick=()=>ask(b.dataset.suggestion,'bank',currentBankId));return;
    }
    if(['announcements','reports','bb-notices'].includes(kind)){
      root.querySelector('h1').textContent=({announcements:tr('কোম্পানির ঘোষণা','Company announcements'),reports:tr('প্রতিবেদন','Reports'),'bb-notices':tr('বাংলাদেশ ব্যাংকের নোটিশ','Bangladesh Bank notices')})[kind];
      let page=1;body.innerHTML='';
      async function more(){try{
        const response=await json(`/v1/institutions/${currentBankId}/publications/${kind}?page=${page}`);if(request!==epoch)return;
        body.querySelector('[data-more]')?.remove();
        const html=response.items.map(row=>window.publicationHTML(row,kind==='announcements'?tr('ডিএসই-তে ব্যাংকের নিজের ঘোষণা','The bank’s own DSE announcement'):kind==='reports'?tr('ব্যাংকের প্রকাশিত প্রতিবেদন','Bank-published report'):tr('বাংলাদেশ ব্যাংকের নোটিশ','Bangladesh Bank notice'))).join('');
        body.insertAdjacentHTML('beforeend',html||empty());
        if(page*20<response.total){body.insertAdjacentHTML('beforeend',`<button type="button" class="catalog-action" data-more>${tr('আরও দেখুন','Show more')}</button>`);body.querySelector('[data-more]').onclick=()=>{body.querySelector('[data-more]').disabled=true;page++;more();};}
      }catch(e){if(request===epoch)error(body,e);}}
      more();return;
    }
    try {
      const rows=await json(`/v1/institutions/${currentBankId}/${({health:'figures',rating:'ratings',news:'events',history:'history'})[kind]}`);
      if(request!==epoch)return;
      if(kind==='history'){renderHistory(body,rows);return;}
      if(!rows.length){body.innerHTML=empty();return;}
      if(kind==='health') {
        const headings={crar:tr('মূলধন অনুপাত','Capital ratio'),npl_ratio:tr('খেলাপি ঋণ','Bad loans'),net_profit:tr('কর-পরবর্তী মুনাফা','Profit after tax')};
        const explanations={crar:tr('লোকসান সামলাতে ব্যাংকের মূলধনের অনুপাত।','Capital available to absorb losses.'),npl_ratio:tr('যে ঋণের কিস্তি সময়মতো ফেরত আসছে না।','Loans whose installments are not being repaid on time.'),net_profit:tr('কর ও খরচ বাদ দেওয়ার পর মুনাফা।','Profit remaining after expenses and tax.')};
        body.innerHTML=Object.keys(headings).map(metric=>{const records=rows.filter(r=>r.metric===metric),r=records[0];if(!r)return empty(headings[metric]+': '+tr('তথ্য নেই','No data'));
          const format=r=>r.unit==='ratio'?percent(r.value*100)+'%':number(r.value/10000000)+' '+tr('কোটি টাকা','crore BDT');
          return `<article class="catalog-card"><h2>${headings[metric]}</h2><p class="catalog-value">${format(r)}</p><p>${digits(r.period)}${r.basis==='consolidated'?' · '+tr('গ্রুপ হিসাব','Group accounts'):''}${String(r.basis).endsWith('_calculated')?' · '+tr('নিরীক্ষকের প্রতিবেদন থেকে হিসাব করা','calculated from the auditor’s report'):''}</p><p>${explanations[metric]}</p>${metric==='crar'?`<p>${tr('ন্যূনতম','Minimum')} ${number(r.legal_min*100)}% <small>${tr('সীমাটি বাংলাদেশ ব্যাংকের নিয়ম থেকে; বিশেষজ্ঞ পর্যালোচনা চলছে','Threshold from Bangladesh Bank rules; expert review in progress')}</small></p>`:''}${metric==='npl_ratio'?`<p>${tr('প্রতি ১০০ টাকার ঋণে','Of each Tk 100 lent, Tk')} ${number(r.value*100)} ${tr('টাকা ফেরত আসছে না।','is not being repaid.')}</p>`:''}${sourceButton(r)}${records.slice(1).map(old=>`<p class="catalog-note">${digits(old.period)}: ${format(old)} ${sourceButton(old)}</p>`).join('')}</article>`;}).join('');wireSources(body,rows);
      } else if(kind==='rating') {
        body.innerHTML=rows.map(r=>`<article class="catalog-card"><h2>${E(r.agency)} · ${E(r.long_term)}</h2><p>${tr('স্বল্পমেয়াদি','Short term')}: ${E(r.short_term||'—')} · ${tr('পূর্বাভাস','Outlook')}: ${E(outlook(r.outlook))}</p><p>${dateText(r.rated_on)} → ${dateText(r.valid_to)} ${r.expired?tr(' · মেয়াদ শেষ',' · Expired'):''}</p><p>${tr('এজেন্সির ঋণ পরিশোধের সক্ষমতা সম্পর্কে মতামত; আমানতের নিশ্চয়তা নয়।','The agency’s opinion of repayment capacity; not a deposit guarantee.')}</p>${sourceButton(r)}</article>`).join('');wireSources(body,rows);
      } else {
        body.innerHTML=rows.map(r=>`<article class="catalog-card"><h2>${E(currentLang==='bn'?r.title_bn:r.title_en)}</h2>${currentLang==='bn'&&!/[\u0980-\u09ff]/.test(r.title_bn)?'<p class="catalog-note">খবরটি ইংরেজিতে</p>':''}<p>${dateText(r.date)}</p><p class="catalog-note">${tr('খবরে প্রকাশিত, নিশ্চিত নয়','Reported in the news, not confirmed')}</p>${r.sources.filter(s=>/^https?:\/\//.test(s.source_url)).map(s=>`<a class="catalog-source" href="${E(s.source_url)}" target="_blank" rel="noopener noreferrer">${tr('মূল সূত্র ↗','Original source ↗')}</a>`).join('')}</article>`).join('');
      }
    }catch(e){if(request===epoch)error(body,e);}
  }

  function renderHistory(body,data) {
    const bn=currentLang==='bn', items=data.items||[];
    body.innerHTML=`<p class="catalog-note">${E(bn?data.message_bn:data.message_en)}</p><p>${tr('এই নথিগুলো বর্তমান অবস্থার রং পরিবর্তন করে না।','These records do not change the current status colour.')}</p>${data.record_window?`<p class="catalog-note">${tr('নথিগুলোর তারিখ','Dates of these records')}: ${dateText(data.record_window.start)} → ${dateText(data.record_window.end)}${tr('। এর বাইরের ঘটনা এখানে না-ও থাকতে পারে।','. Events outside these dates may be missing.')}</p>`:''}${items.length?`<label for="incident-filter">${tr('ঘটনার ধরন','Incident type')}</label><select class="calc-field" id="incident-filter"><option value="">${tr('সব','All')}</option>${[...new Set(items.map(r=>r.kind))].map(kind=>{const row=items.find(r=>r.kind===kind);return `<option value="${E(kind)}">${E(bn?row.type_label_bn:row.type_label_en)}</option>`;}).join('')}</select><div id="incident-rows"></div>`:''}`;
    if(!items.length)return;
    function render(){
      const sources=[];
      $('incident-rows').innerHTML=items.filter(row=>!$('incident-filter').value||row.kind===$('incident-filter').value).map(row=>{
        const proof=row.sources.map(source=>({...source,fact_id:source.source_id}));sources.push(...proof);
        return `<article class="catalog-card"><h2>${E(bn?row.title_bn:row.title_en)}</h2><p>${E(bn?row.confirmation_bn:row.confirmation_en)}</p><p><strong>${E(bn?row.status_label_bn:row.status_label_en)}</strong> · ${dateText(row.last_update_on)}</p>${row.older_history?`<p class="catalog-note">${tr('পুরোনো ঘটনা; বর্তমান আর্থিক অবস্থার প্রমাণ নয়।','Historical record; not evidence of current financial condition.')}</p>`:''}<p>${tr('প্রথম প্রকাশ','First reported')}: ${dateText(row.first_reported_on)}</p><ol>${row.changes.map(change=>`<li>${dateText(change.changed_on)} · ${E(bn?change.status_label_bn:change.status_label_en)}</li>`).join('')}</ol>${proof.map(source=>sourceButton(source)).join('')}</article>`;
      }).join('')||empty();wireSources($('incident-rows'),sources);
    }
    $('incident-filter').onchange=render;render();
  }

  async function enterServices(){
    void loadServiceManifest(); $('main-content').scrollTop=0;$('service-voice-answer').hidden=true;++epoch;servicePage='home';bankFilter=null;renderServicesHome();if(!categories.length)try{categories=await json('/v1/services/categories');}catch{}}
  function serviceHeader(){ $('srv-title').textContent=tr('ব্যাংক সেবা','Bank services');$('srv-subtitle').textContent=tr('একই সেবা, কোথায় খরচ কম?','Same service, where does it cost less?'); }
  function renderServicesHome(){
    $('srv-title').textContent=tr('ব্যাংক সেবা','Bank services');$('srv-subtitle').textContent=tr('একই সেবা, কোথায় খরচ কম?','Same service, where does it cost less?');
    $('services-catalog').innerHTML=`<form class="catalog-search" id="service-search-form"><label class="sr-only" for="service-search-text">${tr('সেবা খুঁজুন','Search services')}</label><input id="service-search-text" placeholder="${tr('সেবা বা প্রশ্ন লিখুন','Type a service or question')}" maxlength="1000" required><button type="submit">${tr('খুঁজুন','Ask')}</button><button type="button" id="service-search-mic" aria-label="${tr('সেবার প্রশ্ন বলুন','Ask a service question by voice')}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/></svg></button></form><div class="catalog-tiles">${[['deposit','◈','জমা ও সঞ্চয়','Deposits and savings'],['card','▣','কার্ড','Cards'],['loan','⌂','ঋণ','Loans'],['account_fee','≡','অ্যাকাউন্ট','Accounts']].map(([key,icon,b,e])=>`<button class="catalog-tile" type="button" data-category="${key}"><span aria-hidden="true">${icon}</span><strong>${tr(b,e)}</strong></button>`).join('')}</div><p class="catalog-note">${tr('৯টি ব্যাংকের প্রকাশিত হার ও ফি। তারিখ প্রতিটি সংখ্যার পাশে।','Published rates and fees of 9 banks. Dates appear beside each number.')}</p><div class="catalog-suggestions">${[['কোন ব্যাংকে ১ বছরের এফডিআর-এ হার বেশি?','Which bank has a higher 1-year FDR rate?'],['সিগনেচার কার্ডের বার্ষিক ফি কোথায় কম?','Where is the Signature card annual fee lower?'],['২০ লাখ টাকার গৃহঋণে মাসিক কিস্তি কত?','What is the EMI on a 20 lakh home loan?']].map(([b,e])=>`<button type="button" class="catalog-detail-row" data-service-suggestion="${E(tr(b,e))}">${E(tr(b,e))}</button>`).join('')}</div>`;
    $('services-catalog').querySelectorAll('[data-category]').forEach(button=>button.onclick=()=>openComparison(({deposit:{product_type:'fdr',tenor_months:12},card:{product_type:'card',network:'Visa',tier:'Gold'},loan:{product_type:'home_loan'},account_fee:{product_type:'account_fee'}})[button.dataset.category]));
    $('service-search-mic').onclick=()=>voice('services');
    $('service-search-form').onsubmit=e=>{e.preventDefault();ask($('service-search-text').value,'services');};
    $('services-catalog').querySelectorAll('[data-service-suggestion]').forEach(b=>b.onclick=()=>ask(b.dataset.serviceSuggestion,'services'));
  }
  function valueText(row){if(row.product_type==='card'&&row.attribute==='fee_waiver_rule')return conditionText(row)||'—';if(row.product_type==='card'&&(/^(?:free|0)$/i.test(row.value_text.trim())))return tr('বিনামূল্যে','Free');if(row.product_type==='card'&&/^\d+(?:\.\d+)?%$/.test(row.value_text.trim()))return digits(row.value_text.trim())+(row.unit==='pct_year'?' '+tr('বার্ষিক','per year'):'');if((row.value_num===0&&/^free$/i.test(row.value_text)||row.value_num==null&&row.value_text==='0')&&/\bfree\b/i.test(row.quote))return tr('বিনামূল্যে','Free');return row.value_num==null?E(digits(row.value_text)):(row.unit==='pct_year'?percent(row.value_num):number(row.value_num))+(row.unit==='pct_year'?'%'+(['rate','rate_min','rate_max','interest_rate'].includes(row.attribute)?' '+tr('বার্ষিক','per year'):''):row.unit==='bdt'?' '+tr('টাকা','BDT'):'');}
  function options(values,selected,formatter=value=>value){
    const missing=selected!=null&&!values.some(value=>String(value)===String(selected));
    const choices=missing?[selected,...values]:values;
    return choices.map(value=>`<option value="${E(value)}" ${String(value)===String(selected)?'selected':''}>${E(formatter(value))}${missing&&String(value)===String(selected)?' · '+tr('প্রকাশিত পছন্দ নেই','no published option'):''}</option>`).join('');
  }
  async function openComparison(next,calculator={}){ stopAudio(); $('main-content').scrollTop=0;
    if(currentTab!=='services')switchTab('services');
    choice={...next,basis:next.basis||'conventional'};bankFilter=null;servicePage='compare';
    calculatorPrefill=calculator;$('service-voice-answer').hidden=!calculator.fromVoice;
    const request=++epoch,root=$('services-catalog');root.innerHTML=empty(tr('একটু অপেক্ষা করুন…','Please wait…'));
    try{if(!categories.length)categories=await json('/v1/services/categories');
      const data=await json('/v1/services/compare?'+new URLSearchParams(Object.fromEntries(Object.entries(choice).filter(([,v])=>v!=null))));
      if(request!==epoch)return;comparison=data;renderComparison();
    }catch(e){if(request===epoch)error(root,e);}
  }
  function renderComparison(){
    serviceHeader();
    const root=$('services-catalog'),category=choice.product_type==='card'?'card':['fdr','dps','savings'].includes(choice.product_type)?'deposit':choice.product_type==='account_fee'?'account_fee':'loan';
    const data=categories.find(c=>c.category===category)||{}, isDeposit=category==='deposit',isLoan=category==='loan';
    const types=category==='deposit'?['fdr','dps','savings']:category==='loan'?['home_loan','auto_loan','personal_loan','loan_against_fdr']:[choice.product_type];
    root.innerHTML=`${back('services-back',tr('ব্যাংক সেবা','Bank services'))}${comparison._offline?`<p class="catalog-note">${tr('অফলাইন কপি — তথ্যের তারিখ দেখুন।','Offline copy — check the document dates.')}</p>`:''}<h2>${E(label(choice.product_type))}</h2><div class="catalog-selectors">${category!=='card'?`<label>${tr('পণ্য','Product')}<select id="compare-product">${options(types,choice.product_type,label)}</select></label>`:''}
      ${['fdr','dps'].includes(choice.product_type)?`<label>${tr('মেয়াদ (মাস)','Tenor (months)')}<select id="compare-tenor">${options([3,6,12,24,36],choice.tenor_months,digits)}</select></label>`:''}
      ${category==='card'?`<label>${tr('নেটওয়ার্ক','Network')}<select id="compare-network">${options(data.networks||[],choice.network)}</select></label><label>${tr('স্তর','Tier')}<select id="compare-tier">${options((data.choices||[]).filter(pair=>pair[0]===choice.network).map(pair=>pair[1]),choice.tier)}</select></label>`:''}
      ${category==='account_fee'?`<label>${tr('বিষয়','Item')}<select id="compare-attribute">${options(data.attributes||[],choice.attribute||'maintenance_fee_half_yearly',label)}</select></label>`:''}
      ${category!=='card'?`<label>${tr('হিসাবের ধরন','Basis')}<select id="compare-basis">${options(['conventional','islamic'],choice.basis,v=>v==='islamic'?tr('ইসলামী','Islamic'):tr('প্রচলিত','Conventional'))}</select></label>`:''}</div>${category==='card'?cardCompareControls():''}
      ${isDeposit||isLoan?`<div class="catalog-calculator"><label for="comparison-example">${tr('একটি উদাহরণ দেখুন — আপনার টাকার পরিমাণ নয়','Choose an example — not your own balance')}</label><select id="comparison-example" class="calc-field">${options([100000,200000,500000,1000000],isLoan?500000:100000,value=>number(value/100000)+' '+tr('লাখ টাকা','lakh BDT'))}</select><p class="catalog-note">${tr('নির্দিষ্ট উদাহরণের হিসাব। ব্যক্তিগত পরিমাণ চাওয়া বা সংরক্ষণ করা হয় না।','Fixed examples only. Your personal amount is neither requested nor stored.')}</p>${isLoan?`<label for="comparison-term">${tr('ঋণের মেয়াদ (মাস)','Loan term (months)')}</label><input id="comparison-term" class="calc-field" type="number" min="1" max="600" value="${Number.isFinite(calculatorPrefill.term)?Math.min(600,Math.max(1,calculatorPrefill.term)):240}">`:''}</div>`:''}
      <p class="comparison-sort-note">${comparison.sort==='higher_rate_first'?tr('বেশি হার আগে','Higher rate first'):tr('কম খরচ আগে','Lower cost first')} · ${tr('প্রকাশিত সংখ্যার ক্রম, ব্যাংকের র‌্যাঙ্কিং নয়','Sorted by published number, not a bank ranking')}</p>${comparison.unit_note_bn&&category!=='card'?`<p class="catalog-note">${E(currentLang==='bn'?comparison.unit_note_bn:comparison.unit_note_en)}</p>`:''}${category!=='card'?`<p id="service-savings" class="catalog-saving" role="status"></p>`:''}<button type="button" id="compare-listen" class="catalog-action btn-primary-listen">${comparisonListenLabel()}</button>${category==='card'?`<p class="catalog-note audio-overview-note">${tr('আপনার নির্বাচিত বিষয়ের তথ্য ও শর্ত শুনুন। নিচে একই বিষয়ের বিস্তারিত লেখা ও সূত্র আছে।','Listen to the facts and conditions for your selected cost. Read its details and sources below.')}</p><details id="comparison-audio-transcript"><summary>${tr('নির্বাচিত বিষয়ের অডিওলিপি পড়ুন','Read the selected-cost audio transcript')}</summary><div id="comparison-narration" class="catalog-note"></div></details>`:`<p id="comparison-narration" class="catalog-note" hidden></p>`}<p id="comparison-audio-error" role="status" hidden></p>${category==='card'?`<article id="card-explanation" class="card-explanation" aria-labelledby="card-explanation-title"></article>`:''}<div id="comparison-rows"></div>${comparison.insurance?`<p class="catalog-note">${E(currentLang==='bn'?comparison.insurance.text_bn:comparison.insurance.text_en)} ${comparison.insurance.source_url?`<a class="catalog-source" href="${E(comparison.insurance.source_url)}" target="_blank" rel="noopener noreferrer">${tr('আইনের সূত্র ↗','Legal source ↗')}</a>`:''}</p>`:isDeposit?`<p class="catalog-note">${tr('বীমার যাচাইকৃত সূত্র এখনও যোগ করা হয়নি।','A verified insurance source has not been loaded yet.')}</p>`:''}`;
    $('services-back').onclick=enterServices;
    if($('compare-product'))$('compare-product').onchange=e=>openComparison({product_type:e.target.value,tenor_months:['fdr','dps'].includes(e.target.value)?12:undefined,basis:choice.basis});
    if($('compare-tenor'))$('compare-tenor').onchange=e=>openComparison({...choice,tenor_months:Number(e.target.value)});
    if($('compare-network'))$('compare-network').onchange=e=>{const tiers=(data.choices||[]).filter(p=>p[0]===e.target.value).map(p=>p[1]);openComparison({...choice,network:e.target.value,tier:tiers.includes(choice.tier)?choice.tier:tiers[0]});};
    if($('compare-tier'))$('compare-tier').onchange=e=>openComparison({...choice,tier:e.target.value});
    if($('compare-attribute'))$('compare-attribute').onchange=e=>openComparison({...choice,attribute:e.target.value});
    if($('compare-basis'))$('compare-basis').onchange=e=>openComparison({...choice,basis:e.target.value});
    if($('comparison-example'))$('comparison-example').onchange=renderRows;
    if($('comparison-term'))$('comparison-term').oninput=renderRows;
    $('compare-listen').onclick=listenComparison;
    if(category==='card'){$('card-compare-by').onchange=async event=>{await openComparison({...choice,attribute:undefined,compare_by:event.target.value});$('card-compare-by')?.focus({preventScroll:true});};$('card-meanings').onclick=()=>{const sheet=$('card-meaning-dialog');sheet.showModal();};$('card-meaning-close').onclick=()=>$('card-meaning-dialog').close();}
    if(category==='card'){renderCardExplanation();renderAudioTranscript();}
    renderRows();
  }
  function renderRows(){
    if(choice.product_type==='card')return renderCardRows();
    const root=$('comparison-rows');
    const amount=Number($('comparison-example')?.value)||100000;
    const months=Math.min(600,Math.max(1,Number($('comparison-term')?.value)||1));
    const deposit=['fdr','dps','savings'].includes(choice.product_type), loan=choice.product_type.endsWith('_loan')||choice.product_type==='loan_against_fdr';
    root.innerHTML=comparison.rows.map(bank=>{const row=bank.offer;
      if(!row)return `<div class="catalog-offer-row muted">${bankNames(bank)}<p>${bank.state==='checking'?tr('তথ্য যাচাই হচ্ছে','Data being checked'):bank.state==='not_published'?tr('প্রকাশিত নয়','Not published'):tr('তথ্য নেই','No data')}</p>${statusChip(bank)}</div>`;
      let calculation='';
      if(row.value_num!=null&&row.unit==='pct_year') {
        if(deposit&&choice.tenor_months)calculation=`${digits(choice.tenor_months)} ${row.basis==='islamic'?tr('মাসে আনুমানিক মুনাফা','months provisional profit'):tr('মাসে সুদ','months interest')}: ${number(amount*row.value_num/100*choice.tenor_months/12)} ${tr('টাকা · আনুমানিক, কর কাটার আগে','BDT · estimate, before tax')}`;
        if(loan){const rate=row.value_num/1200,emi=rate===0?amount/months:amount*rate/(1-Math.pow(1+rate,-months));calculation=`${tr('আনুমানিক কিস্তি','Estimated installment')}: ${number(emi)} ${tr('টাকা/মাস','BDT/month')}`;}
      }
      const year3=choice.product_type==='card'&&row.attribute==='annual_fee'&&!row.stale&&!bank.renewal_offer?.stale&&row.value_num!=null&&bank.renewal_offer?.value_num!=null?`${tr('৩ বছরে মোট','Total over 3 years')}: ${number(row.value_num+2*bank.renewal_offer.value_num)} ${tr('টাকা','BDT')}`:'';
      return `<article class="catalog-offer-row"><button class="catalog-open-offer" type="button" data-offer="${E(row.offer_id)}" aria-label="${E(bankName(bank)+' · '+label(row.attribute)+' · '+valueText(row)+' · '+dateText(row.doc_date))}">${bankNames(bank)}<span class="catalog-note">${E(label(row.attribute))}</span><span class="catalog-value">${valueText(row)}</span><span>${E(productText(row))}</span></button><p>${E(conditionText(row))}</p><p>${dateText(row.doc_date)} ${row.stale?`<span class="catalog-stale">${tr('পুরনো তথ্য','Old data')}</span>`:''}</p>${row.basis==='islamic'?`<p>${tr('মুনাফার হার (আনুমানিক)','Profit rate (provisional)')}</p>`:''}${offerStatus(bank)}${sourceButton(row,bank)}${bank.range_max?`<p>${tr('সর্বনিম্ন–সর্বোচ্চ','Minimum–maximum')}: ${valueText(row)} – ${valueText(bank.range_max)} ${sourceButton(bank.range_max,bank)}</p>`:''}<p class="catalog-note">${E(calculation)}</p><p>${E(year3)}</p>${(bank.alternatives||[]).length?(choice.product_type==='card'?`<details class="catalog-variants"><summary>${tr(`আরও ${digits(bank.alternatives.length)}টি সংস্করণ`,`${bank.alternatives.length} more versions`)}</summary>${bank.alternatives.map(variant=>`<article class="catalog-card"><button type="button" class="catalog-open-offer" data-offer="${E(variant.offer_id)}"><strong>${E(productText(variant))}</strong><span class="catalog-value">${valueText(variant)}</span></button><p>${dateText(variant.doc_date)}${variant.stale?' · '+tr('পুরনো তথ্য','Old data'):''}</p><p>${E(conditionText(variant))}</p>${sourceButton(variant,bank)}</article>`).join('')}</details>`:`<p class="catalog-note">${tr('অন্য স্ল্যাব ও পণ্যের শর্ত বিস্তারিত পাতায় দেখুন।','Other slabs/products have different conditions; inspect the product details.')}</p>`):''}</article>`;
    }).join('');
    root.querySelectorAll('[data-offer]').forEach(button=>button.onclick=()=>openOffer(button.dataset.offer));
    wireSources(root,comparison.rows.flatMap(bank=>[bank.offer,bank.range_max,...(bank.alternatives||[])].filter(Boolean)));
    const fresh=comparison.rows.filter(b=>b.offer?.value_num!=null&&!b.offer.stale);
    if(choice.product_type==='card'&&['annual_fee','renewal_fee'].includes(comparison.choice.attribute)&&fresh.length>1){const ordered=[...fresh].sort((a,b)=>a.offer.value_num-b.offer.value_num),a=ordered[0],b=ordered.at(-1);
      $('service-savings').textContent=tr(`${bankName(a)}-এর ফি ${bankName(b)}-এর চেয়ে বছরে ${number(b.offer.value_num-a.offer.value_num)} টাকা কম।`,`${bankName(a)} costs BDT ${number(b.offer.value_num-a.offer.value_num)} less per year than ${bankName(b)}.`);
    }else $('service-savings').textContent='';
  }
  async function openOffer(id){ $('main-content').scrollTop=0;
    $('service-voice-answer').hidden=true;const request=++epoch,root=$('services-catalog');servicePage='offer';root.innerHTML=empty(tr('একটু অপেক্ষা করুন…','Please wait…'));
    try{const data=await json('/v1/services/offers/'+encodeURIComponent(id));if(request!==epoch)return;offerDetail=data;renderOffer();}catch(e){if(request===epoch)error(root,e);}
  }
  function renderOffer(){const root=$('services-catalog'),data=offerDetail;
    if(data.offers[0]?.product_type==='card')return renderCardOffer();
    serviceHeader();
    root.innerHTML=`${back('offer-back',tr('ফিরুন','Back'))}<h2>${E(bankName(data.institution))}</h2>${statusChip(data.institution)}<h3>${E(productText(data.offers[0]||{product:data.product}))}</h3>${data.offers[0]?.variant==='excluded'?`<p class="catalog-note">${tr('সীমিত বা বিশেষ কার্ড — সাধারণ গ্রাহকের তুলনায় অন্তর্ভুক্ত নয়।','Restricted or special card — excluded from retail comparisons.')}</p>`:''}${data.offers.map(row=>`<article class="catalog-card"><h3>${E(label(row.attribute))}</h3><p class="catalog-value">${valueText(row)}</p><p>${E(conditionText(row))}</p><p>${dateText(row.doc_date)} ${row.stale?tr('· পুরনো তথ্য','· Old data'):''}</p>${sourceButton(row)}</article>`).join('')}<p class="catalog-note">${tr('ব্যাংকের প্রকাশিত তালিকা থেকে। আবেদন করার আগে ব্যাংকের সাথে নিশ্চিত হোন।','From the bank’s published schedule. Confirm with the bank before applying.')}</p><button class="catalog-action" id="offer-bank-report" type="button">${tr('এই ব্যাংকের অবস্থা দেখুন','See this bank’s condition')}</button>`;
    wireSources(root,data.offers);$('offer-bank-report').onclick=()=>openBank(data.institution.id);$('offer-back').onclick=()=>bankFilter?openBankServices(bankFilter):openComparison(choice);
  }
  async function openBankServices(id){ $('main-content').scrollTop=0;if(currentTab!=='services')switchTab('services');bankFilter=id;servicePage='bank';const request=++epoch,root=$('services-catalog');root.innerHTML=empty(tr('একটু অপেক্ষা করুন…','Please wait…'));
    try{const data=await json(`/v1/institutions/${id}/services`);if(request!==epoch)return;bankOffers=data;renderBankServices();}catch(e){if(request===epoch)error(root,e);}
  }
  function renderBankServices(){const data=bankOffers,root=$('services-catalog'),groups=new Map();data.offers.forEach(r=>{if(!groups.has(r.group_key))groups.set(r.group_key,r);});
    serviceHeader();
    root.innerHTML=`${back('bank-services-back',tr('ব্যাংক সেবা','Bank services'))}<h2>${E(bankName(data.institution))}</h2>${statusChip(data.institution)}${['deposit','card','loan','account_fee'].map(category=>`<h3>${E(({deposit:tr('জমা ও সঞ্চয়','Deposits and savings'),card:tr('কার্ড','Cards'),loan:tr('ঋণ','Loans'),account_fee:tr('অ্যাকাউন্ট','Accounts')})[category])}</h3>${category==='card'?bankCardLines(data.offers):[...groups.values()].filter(r=>r.category===category).map(r=>`<button class="catalog-detail-row" data-bank-offer="${E(r.offer_id)}" type="button">${E(productText(r))} ›</button>`).join('')||empty()}`).join('')}`;
    $('bank-services-back').onclick=enterServices;root.querySelectorAll('[data-bank-offer]').forEach(b=>b.onclick=()=>openOffer(b.dataset.bankOffer));
  }
  const cardCompareFacts=['annual_fee','interest_rate','late_fee','cash_advance_fee','foreign_currency_markup'];
  const cardLabels={annual_fee:['বার্ষিক ফি','Annual fee'],interest_rate:['সুদের হার','Interest rate'],late_fee:['বিলম্ব ফি','Late fee'],cash_advance_fee:['নগদ তোলার ফি','Cash withdrawal fee'],foreign_currency_markup:['বিদেশে খরচ','Foreign spending'],supplementary_card_fee:['অতিরিক্ত কার্ড','Supplementary card'],lounge_access:['লাউঞ্জ','Lounge'],card_replacement_fee:['কার্ড হারালে নতুন কার্ডের ফি','Replacement card'],renewal_fee:['নবায়ন ফি','Renewal fee'],fee_waiver_rule:['ফি মওকুফের শর্ত','Fee waiver']};
  const cardLabel=key=>(cardLabels[key]||[label(key),label(key)])[currentLang==='bn'?0:1];
  const cardStatus=bank=>bank.status?.code==='no_data'?`<span class="catalog-status no_data">${tr('? অবস্থা যাচাই হয়নি','? Condition unverified')}</span>`:statusChip(bank);
  const cardValue=row=>row?valueText(row):'—';
  const detailCondition=row=>{const text=conditionText(row);return text==='+১৫% ভ্যাট'||text==='+15% VAT'?'':text;};
  function cardCompareControls(){
    const meanings=['বার্ষিক ফি: কার্ড রাখার জন্য প্রতি বছর যা কাটে','সুদের হার: পুরো বিল সময়মতো না দিলে বাকি টাকার উপর বছরে যত সুদ','বিলম্ব ফি: শেষ তারিখের পরে বিল দিলে প্রতিবার যা কাটে','নগদ তোলার ফি: কার্ড দিয়ে এটিএম থেকে টাকা তুললে যা কাটে','বিদেশে খরচ: ডলার ছাড়া অন্য মুদ্রায় কেনাকাটায় অতিরিক্ত যা কাটে','অতিরিক্ত কার্ড: পরিবারের কারো জন্য দ্বিতীয় কার্ডের ফি'];
    const english=['Annual fee: yearly cost of keeping the card','Interest: annual rate on an unpaid balance','Late fee: charge when a bill is paid after its due date','Cash withdrawal: charge for taking cash using the card','Foreign spending: extra charge for purchases in currencies other than USD','Supplementary card: fee for an extra family card'];
    return `<div class="card-compare-controls"><div class="card-compare-heading"><label for="card-compare-by">${tr('কী তুলনা করবেন','Compare by')}</label><button type="button" id="card-meanings" aria-haspopup="dialog" aria-label="${tr('খরচের অর্থ জানুন','Explain these costs')}">ⓘ</button></div><select id="card-compare-by">${options(cardCompareFacts,choice.compare_by||choice.attribute||'annual_fee',cardLabel)}</select></div><dialog id="card-meaning-dialog" class="settings-dialog"><h2>${tr('খরচের অর্থ','What these costs mean')}</h2>${(currentLang==='bn'?meanings:english).map(text=>`<p>${text}</p>`).join('')}<button type="button" id="card-meaning-close">${tr('বন্ধ করুন','Close')}</button></dialog>`;
  }
  function renderCardRows(){
    const primary=comparison.choice.attribute;const sources=[];
    $('comparison-rows').innerHTML=comparison.rows.map(bank=>{
      const card=bank.card||bank.offer;
      if(!card)return `<p class="catalog-offer-row muted">${E(bankName(bank))} · ${bank.state==='checking'?tr('তথ্য যাচাই হচ্ছে','Data being checked'):tr('এই স্তরের কার্ড প্রকাশিত নয়','No card published in this tier')}</p>`;
      const row=bank.offer,facts=bank.facts||{};sources.push(...Object.values(facts).filter(Boolean));
      const grid=['interest_rate','late_fee','cash_advance_fee','foreign_currency_markup','supplementary_card_fee','lounge_access'].map(key=>key===primary?'annual_fee':key);
      const cell=key=>{const fact=facts[key];return `<${fact?'button':'div'} ${fact?`type="button" data-source="${E(fact.offer_id)}"`:''} class="card-fact-cell ${fact?'':'muted'}"><span>${E(cardLabel(key))}</span><strong>${E(fact&&key==='cash_advance_fee'&&conditionText(fact).includes('অথবা')?conditionText(fact):fact&&key==='supplementary_card_fee'&&conditionText(fact).includes('প্রথম')?conditionText(fact).replace('প্রথম অতিরিক্ত কার্ড','প্রথমটি'):cardValue(fact))}</strong>${fact?.stale?`<small>${tr('পুরনো তথ্য','Old data')}</small>`:''}</${fact?'button':'div'}>`;};
      const waiver=facts.fee_waiver_rule;const displayDate=row?.doc_date||card.doc_date;
      return `<article class="catalog-offer-row card-tile"><div class="card-bank-heading"><div>${bankNames(bank)}</div>${cardStatus(bank)}</div><h3>${E(productText(card))}</h3>${card.card_printed_name?`<small lang="en">${E(card.card_printed_name)}</small>`:''}<div class="card-top-fact"><span>${E(cardLabel(primary))}</span><strong class="catalog-value">${E(cardValue(row))}</strong>${row&&conditionText(row)?`<small>${E(conditionText(row))}</small>`:''}</div>${waiver?`<p class="card-waiver">${E(conditionText(waiver)||tr('ফি মওকুফের শর্ত মূল সূত্রে দেখুন','See source for fee waiver terms'))}</p>`:''}<div class="card-fact-grid">${grid.map(cell).join('')}</div><footer class="card-tile-footer"><small>${dateText(displayDate)} ${row?.stale||card.stale?`<span class="catalog-stale">${tr('পুরনো তথ্য','Old data')}</span>`:''}</small><button type="button" data-offer="${E(card.offer_id)}">${tr('সব বিবরণ ›','All details ›')}</button>${row?sourceButton(row,bank):''}</footer>${bank.alternatives.length?`<details><summary>${tr(`আরও ${digits(bank.alternatives.length)}টি সংস্করণ`,`${bank.alternatives.length} more versions`)}</summary>${bank.alternatives.map(v=>{sources.push(v);return `<article class="card-variant"><strong>${E(v.card_printed_name||productText(v))}</strong><p>${E(cardValue(v))}</p><button type="button" data-offer="${E(v.offer_id)}">${tr('সব বিবরণ ›','All details ›')}</button></article>`;}).join('')}</details>`:''}</article>`;
    }).join('');
    $('comparison-rows').querySelectorAll('[data-offer]').forEach(button=>button.onclick=()=>openOffer(button.dataset.offer));wireSources($('comparison-rows'),sources);

  }
  function renderCardOffer(){
    const root=$('services-catalog'),data=offerDetail,card=data.offers.find(r=>r.attribute==='annual_fee')||data.offers[0];serviceHeader();
    const sections=[['প্রতি বছরের খরচ','Yearly costs',['annual_fee','renewal_fee','fee_waiver_rule','supplementary_card_fee']],['বিল দেরিতে দিলে বা টাকা তুললে','Late bills and cash',['interest_rate','late_fee','cash_advance_fee']],['বিদেশে ব্যবহার','Use abroad',['foreign_currency_markup']],['অন্যান্য','Other',['card_replacement_fee','lounge_access']]];
    const facts=Object.fromEntries(data.offers.map(row=>[row.attribute,row]));
    const annual=facts.annual_fee,renewal=facts.renewal_fee;
    const total=annual?.value_num!=null&&renewal?.value_num!=null&&!annual.stale&&!renewal.stale?`<p>${tr('৩ বছরে মোট বার্ষিক ফি','Total annual fees over 3 years')}: ${number(annual.value_num+2*renewal.value_num)} ${tr('টাকা','BDT')}</p>`:'';
    root.innerHTML=`${back('offer-back',tr('ফিরুন','Back'))}<h2>${E(bankName(data.institution))}</h2>${cardStatus(data.institution)}<h3>${E(productText(card))}</h3>${card.card_printed_name?`<small lang="en">${E(card.card_printed_name)}</small>`:''}<p class="catalog-meta">${dateText(card.doc_date)}</p>${sections.map(([bn,en,keys])=>`<section class="card-detail-section"><h3>${tr(bn,en)}</h3>${keys.map(key=>{const row=facts[key];return `<article class="card-detail-fact"><span>${cardLabel(key)}</span><strong>${E(cardValue(row))}</strong>${row?`<small>${E(detailCondition(row))}</small><small>${dateText(row.doc_date)} ${row.stale?tr('পুরনো তথ্য','Old data'):''}</small>${sourceButton(row)}`:''}</article>`;}).join('')}</section>`).join('')}${total}${data.offers.some(r=>/15\s*%\s*vat/i.test(r.condition+' '+r.value_text+' '+r.quote))?`<p>${tr('ফির সাথে ১৫% ভ্যাট যোগ হয়','15% VAT is added to fees')}</p>`:''}<p class="catalog-note">${tr('ব্যাংকের প্রকাশিত তালিকা থেকে। আবেদন করার আগে ব্যাংকের সাথে নিশ্চিত হোন।','From published bank schedules. Confirm with the bank before applying.')}</p><button type="button" class="catalog-action" id="offer-compare">${tr('অন্য ব্যাংকের সাথে তুলনা','Compare with other banks')}</button><button type="button" class="catalog-action" id="offer-bank-report">${tr('এই ব্যাংকের অবস্থা দেখুন','See this bank’s condition')}</button>`;
    wireSources(root,data.offers);$('offer-bank-report').onclick=()=>openBank(data.institution.id);$('offer-back').onclick=()=>bankFilter?openBankServices(bankFilter):openComparison(choice);$('offer-compare').onclick=()=>{bankFilter=null;openComparison({product_type:'card',network:card.network,tier:card.tier});};
  }
  function bankCardLines(rows){
    const cards=rows.filter(r=>r.product_type==='card'&&r.attribute==='annual_fee'&&r.variant!=='excluded');const seen=new Set();
    return [...new Set(cards.map(r=>r.network))].sort().map(network=>`<h4>${E(currentLang==='bn'?cards.find(r=>r.network===network).card_display_bn.split(' ')[0]:network)}</h4>`+cards.filter(r=>r.network===network&&!seen.has(r.card_key)).map(row=>{seen.add(row.card_key);return `<button class="catalog-detail-row" type="button" data-bank-offer="${E(row.offer_id)}">${E(productText(row))}${row.card_printed_name?' · '+E(row.card_printed_name):''} · ${E(cardValue(row))}/${tr('বছর','year')} ›</button>`;}).join('')).join('')||empty();
  }
  function comparisonListenLabel(){return choice.product_type==='card'?tr(cardLabel(choice.compare_by||choice.attribute||'annual_fee')+' সম্পর্কে শুনুন','Listen: '+cardLabel(choice.compare_by||choice.attribute||'annual_fee')):tr('শুনুন','Listen');}
  function renderCardExplanation(){
    const data=comparison.explanation,root=$('card-explanation');if(!data||!root)return;root.dataset.attribute=data.attribute;
    const sources=comparison.rows.flatMap(bank=>Object.values(bank.facts||{}).filter(Boolean));
    root.innerHTML=`<h3 id="card-explanation-title">${E(currentLang==='bn'?data.title_bn:data.title_en)}</h3>${data.sections.map(section=>`<section class="card-explanation-section" data-explanation-section="${E(section.id)}"><h4>${E(currentLang==='bn'?section.heading_bn:section.heading_en)}</h4>${section.paragraphs.map(paragraph=>`<div class="card-explanation-paragraph"><p>${E(currentLang==='bn'?paragraph.text_bn:paragraph.text_en)}</p>${(paragraph.fact_ids||[]).map(id=>sources.find(fact=>fact.offer_id===id)).filter(Boolean).map(fact=>`<button class="catalog-source" type="button" data-source="${E(fact.offer_id)}" aria-label="${E(cardLabel(fact.attribute)+' · '+(comparison.rows.find(bank=>bank.id===fact.institution_id)?bankName(comparison.rows.find(bank=>bank.id===fact.institution_id)):''))}">${E(cardLabel(fact.attribute))} · ${tr('সূত্র ›','Source ›')}</button>`).join(' ')}</div>`).join('')}</section>`).join('')}`;
    wireSources(root,sources);
  }
  function renderAudioTranscript(){
    const root=$('comparison-narration');if(!root)return;
    const text=currentLang==='bn'?comparison.readout?.text:'';
    const paragraphs=text?text.split(/\n\s*\n/).filter(Boolean):[];
    root.innerHTML=paragraphs.map(text=>`<p>${E(text)}</p>`).join('')||`<p>${tr('এই ভাষায় সংরক্ষিত অডিওলিপি নেই। নির্বাচিত বিষয়ের লেখাটি উপরে পড়ুন।','No saved transcript in this language. Read the selected-cost article above.')}</p>`;
  }
  function listenComparison(){
    if(suppressReadoutClick){suppressReadoutClick=false;return;}
    stopAudio();const request=playbackRequest;
    const data=currentLang==='bn'?comparison.readout:null;
    const text=$('comparison-narration'),message=$('comparison-audio-error');
    text.hidden=false;if(choice.product_type==='card'){$('comparison-audio-transcript').open=true;renderAudioTranscript();}else text.textContent=data?.text||tr('এই তুলনার সংরক্ষিত বর্ণনা নেই। নিচের তথ্য পড়ুন।','Saved English narration is not available. Read the comparison below.');
    const failed=()=>{message.hidden=false;message.textContent=tr('এখন শোনানো যাচ্ছে না, লেখাটি পড়ুন','Audio is unavailable now. Please read the text.');};
    message.hidden=true;
    const approved=Object.values(serviceManifest.clips||{}).find(item=>item.reviewed===true&&'/static/audio/services/'+item.file+'?v='+item.audio_sha256?.slice(0,16)===data?.audio_url&&item.text===data?.text);
    if(!approved||!data?.audio_url){failed();return;}
    // No fetch or await here: play() must run during the original tap gesture.
    try{if(!playVoiceAudio(data.audio_url,request,true,failed))failed();}catch{failed();}
  }
  window.IlmaCatalog={
    enter(tab){if(tab==='detail')currentBankId?showReport():showBankList();else if(tab==='services')enterServices();},
    reportReady,openComparison,openBankServices,toggleWatch,listenLabel:comparisonListenLabel,
    relocalize(){if(currentTab==='detail'){if(bankPage==='list')renderBankList();else if(bankPage==='detail')showBankDetail(detailKind);else if(reportCardData)reportReady(reportCardData);}
      if(currentTab==='services'){if(servicePage==='home')renderServicesHome();else if(servicePage==='compare')renderComparison();else if(servicePage==='offer')renderOffer();else if(bankOffers)renderBankServices();}}
  };
})();
