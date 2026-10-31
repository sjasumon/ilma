/* Shared sourced-catalog formatting and request helpers. */
(()=>{
  const $ = id => document.getElementById(id), E = escapeHTML;
  const tr = (bn,en) => currentLang === 'bn' ? bn : en;
  const digits = value => currentLang === 'bn' ? toBnDigits(value) : String(value);
  const dateText = value => value ? new Intl.DateTimeFormat(currentLang==='bn'?'bn-BD':'en-GB',{day:'numeric',month:'long',year:'numeric'}).format(new Date(String(value).slice(0,10)+'T00:00:00')) : '—';
  const number = value => digits(Number(value).toLocaleString('en-IN',{maximumFractionDigits:2}));
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
  const productText = row => row.product_type==='card'?(currentLang==='bn'?row.card_display_bn:row.card_display_en):currentLang==='en'?row.product:[label(row.product_type||(window.IlmaServices?.productType?.()||'fdr')),row.tenor_months?`${digits(row.tenor_months)} মাস`:''].filter(Boolean).join(' · ');
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
  const back = (id,text) => `<button type="button" class="catalog-back" id="${id}"><span class="back-arrow" aria-hidden="true">←</span><span>${E(text)}</span></button>`;
  async function json(url) {
    const response=await fetch(url);
    if(!response.ok) throw Error(tr('তথ্য লোড করা যায়নি। আবার চেষ্টা করুন।','Could not load data. Please try again.'));
    const data=await response.json();
    if(response.headers?.get('X-ILMA-Offline')==='1') {
      data._offline=true;
      data._cachedAt=response.headers.get('X-ILMA-Cached-At')||null;
    }
    return data;
  }
  function offlineNote(data) {
    if(!data?._offline)return '';
    const time=Date.parse(data._cachedAt);
    const saved=Number.isFinite(time)
      ? tr('সংরক্ষণের সময়: ','Saved: ')+new Intl.DateTimeFormat(currentLang==='bn'?'bn-BD':'en-GB',{dateStyle:'medium',timeStyle:'short'}).format(new Date(time))+'. '
      : tr('সংরক্ষণের সময় জানা নেই। ','Saved time is unavailable. ');
    return `<p class="catalog-note catalog-offline" role="status">${E(tr('সংরক্ষিত কপি — তথ্য পুরনো হতে পারে। ','Saved copy — data may be out of date. ')+saved+tr('মূল সূত্রের তারিখ দেখুন।','Check the source document dates.'))}</p>`;
  }
  function focusHeading(root) {
    const panel=root?.closest?.('.tab-content');
    if(panel&&!panel.classList.contains('active'))return;
    const heading=root?.querySelector?.('h1, h2');
    if(!heading)return;
    heading.setAttribute?.('tabindex','-1');
    heading.focus?.({preventScroll:true});
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
  function error(root,failure,retry) {
    // Browser/provider messages vary by platform and are never useful UI copy.
    root.innerHTML=empty(tr('তথ্য আনা যায়নি। সংযোগ দেখুন, তারপর আবার চেষ্টা করুন।','Could not load this information. Check your connection, then try again.'))+`<button type="button" class="catalog-action" data-retry>${tr('আবার চেষ্টা করুন','Try again')}</button>`;
    const button=root.querySelector('[data-retry]');
    button.hidden=typeof retry!=='function';
    const message=root.querySelector('.catalog-empty');
    if(message){message.id=(root.id||'catalog')+'-error';button.setAttribute?.('aria-describedby',message.id);}
    button.focus?.({preventScroll:true});
    button.onclick=()=>{button.disabled=true;return retry();};
  }
  window.IlmaCatalogCommon={$,E,tr,digits,dateText,number,label,outlook,percent,bankName,statusChip,bankNames,productText,conditionText,offerStatus,empty,back,json,offlineNote,focusHeading,sourceButton,wireSources,voice,ask,error,state:{epoch:0}};
})();
