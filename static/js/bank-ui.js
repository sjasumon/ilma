/* Bank list, report and sourced section screens. */
(()=>{
  const {$,E,tr,digits,dateText,number,label,outlook,percent,bankName,bankNames,productText,conditionText,offerStatus,back,json,offlineNote,focusHeading,sourceButton,wireSources,voice,ask,error,state}=window.IlmaCatalogCommon;
  let banks=[],bankPage='list',detailKind='health',search='';
  const openBankServices=(...args)=>window.IlmaServices.openBankServices(...args);
  const empty=text=>text?`<p class="catalog-empty" role="status">${E(text)}</p>`:'';
  const riskWords={strong:['ঝুঁকি কম','Low risk'],watch:['ঝুঁকি মাঝারি','Medium risk'],high:['ঝুঁকি বেশি','High risk'],no_data:['মূল্যায়ন করা হয়নি','Not rated']};
  const statusChip=bank=>`<span class="catalog-status ${E(bank.status?.code||'no_data')}">${({strong:'✓ ',watch:'⚠ ',high:'✕ ',no_data:''})[bank.status?.code||'no_data']}${E(riskWords[bank.status?.code||'no_data'][currentLang==='bn'?0:1])}</span>`;
  function listenReport(){
    if(suppressReadoutClick){suppressReadoutClick=false;return;}
    stopAudio();const saved=reportCardData?.readout;
    $('bank-report-transcript').textContent=saved?.text||'';$('bank-report-transcript').lang='bn';$('bank-report-transcript').hidden=false;
    const failed=()=>{$('bank-report-audio-error').hidden=false;$('bank-report-audio-error').textContent=tr('এখন শোনানো যাচ্ছে না, লেখাটি পড়ুন','Audio is unavailable now. Please read the text.');};
    $('bank-report-audio-error').hidden=true;
    if(!saved?.audio_url||!playVoiceAudio(saved.audio_url,playbackRequest,true,failed))failed();
  }
  function reportView(show) {
    $('main-content').scrollTop=0;
    $('bank-list-view').hidden=show;
    $('bank-report-view').hidden=!show;
    $('bank-detail-view').hidden=true;
  }
  async function showBankList() {
    window.IlmaNavigation?.visit({screen:"banks"});
    ++reportRequest; reportCardData=null;bankPage='list'; currentBankId=null; reportView(false); $('bank-list-view').hidden=false;
    const root=$('bank-list-view'), request=++state.epoch;
    root.innerHTML=empty(tr('একটু অপেক্ষা করুন…','Please wait…'));
    try { banks=await json('/v1/institutions?list=demo'); if(request!==state.epoch)return; renderBankList();focusHeading?.(root); }
    catch(e){if(request===state.epoch)error(root,e,showBankList);}
  }
  function renderBankList() {
    const root=$('bank-list-view');
    root.innerHTML=`${offlineNote(banks)}<div class="screen-header"><h1>${tr('ব্যাংক','Banks')}</h1><p>${tr('কোন ব্যাংকের ঝুঁকি জানতে চান?','Which bank do you want to check?')}</p>
      <div class="catalog-search"><label class="sr-only" for="bank-list-search">${tr('ব্যাংকের নাম লিখুন','Type a bank name')}</label><input id="bank-list-search" type="search" placeholder="${tr('ব্যাংকের নাম লিখুন','Type a bank name')}"><button type="button" id="bank-list-mic" aria-label="${tr('ব্যাংকের নাম বলুন','Say a bank name')}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/></svg></button></div></div>
      <div class="sheet"><div id="bank-list-rows"></div><p class="catalog-note">${tr(`${digits(banks.length)}টি ব্যাংকের প্রকাশিত তথ্য`,`Published information for ${banks.length} banks`)}</p><button type="button" class="catalog-source" id="prior-work">${tr('তথ্য কোথা থেকে এসেছে','Where the data comes from')}</button></div>`;
    $('bank-list-search').value=search;
    function rows(){search=$('bank-list-search').value;const query=search.trim().toLowerCase();
      const name=currentLang==='en'?'name_en':'name_bn';
      $('bank-list-rows').innerHTML=banks.filter(b=>`${b.name_bn} ${b.name_en} ${b.slug} ${(b.aliases||[]).join(" ")}`.toLowerCase().includes(query)).sort((a,b)=>a[name].localeCompare(b[name],currentLang==='en'?'en':'bn')).map(bank=>
        `<button class="catalog-bank-row" type="button" data-bank="${bank.id}"><span>${bankNames(bank)}</span>${statusChip(bank)}</button>`).join('')||empty();
      root.querySelectorAll('[data-bank]').forEach(button=>button.onclick=()=>openBank(Number(button.dataset.bank)));
    }
    rows(); $('bank-list-search').oninput=rows; $('bank-list-mic').onclick=()=>voice('bank');
    $('prior-work').onclick=()=>openProofModal(tr('তথ্য কোথা থেকে এসেছে','Where the data comes from'),tr(
      'উৎসের তথ্য প্রকল্পের আগে সংগ্রহ করা হয়েছিল। প্রতিটি সংখ্যার উদ্ধৃতি ও মূল নথির সংযোগ দেখুন। সংবাদমাধ্যমের খবর ও সরকারি নথি আলাদাভাবে চিহ্নিত করা হয়।',
      'Source collection predates this project. See each quotation and original document. News reports and official documents are labelled separately.'),'',null,null);
  }
  function showReport() { window.IlmaNavigation?.visit({screen:'report',bank:currentBankId}); ++state.epoch; bankPage='report';reportView(true);$('btn-watch-bank').setAttribute('aria-pressed','false');$('btn-watch-bank').disabled=true;$('bank-list-back').onclick=showBankList;return loadReportCard(currentBankId); }
  function reportReady(data) {
    const bn=currentLang==='bn', bank=data.institution;
    $('bank-list-back').textContent='← '+tr('ব্যাংক','Banks');$('bank-list-back').onclick=showBankList;
    $('card-bank-meta').textContent=bn?bank.name_en:'';
    $('bank-profile-chips').innerHTML=[data.founded_year?tr('প্রতিষ্ঠা ','Founded ')+digits(data.founded_year):'',data.data_date?digits(data.data_date.slice(0,4))+tr(' সালের নিরীক্ষিত তথ্য',' audited figures'):''].filter(Boolean).map(text=>`<span class="bank-meta-chip">${E(text)}</span>`).join('');
    if(data.founding_source){const chip=$('bank-profile-chips').firstElementChild;if(chip){const button=document.createElement('button');button.className='bank-meta-chip';button.type='button';button.textContent=chip.textContent;button.onclick=()=>openProofModal(tr('প্রতিষ্ঠার বছর','Founding year'),(data.founding_source.summary?tr('সূত্রের সারাংশ: ','Source summary: '):'')+data.founding_source.quote,data.founding_source.source_url,data.founding_source.page);chip.replaceWith(button);}}
    $('bank-profile-facts').innerHTML=(data.profile_facts||[]).length?`<h2>${tr('পরিচিতি','Profile')}</h2>${data.profile_facts.map(f=>`<p>${E(bn?digits(f.fact_bn):f.fact_en||f.fact_bn)} <a class="catalog-source" href="${E(f.source_url)}" target="_blank" rel="noopener noreferrer">${tr('সূত্র ↗','Source ↗')}</a>${f.as_of?`<small>${dateText(f.as_of)}</small>`:''}${f.source_note?`<small>${E(bn?f.source_note:f.source_note_en||'')}</small>`:''}</p>`).join('')}`:'';
    if(data.comparison_facts?.length)$('bank-profile-facts').insertAdjacentHTML('beforeend',data.comparison_facts.map(group=>`<details><summary>${E(bn?group.title_bn:group.title_en)}</summary><p class="catalog-note">${tr('এই তালিকার ব্যাংকগুলোর প্রকাশিত অনুপাত থেকে হিসাব; যেসব অনুপাতের সূত্র আছে, সেগুলো দেখানো হয়েছে।','Calculated from sourced ratios in this bank list; only published observations are shown.')}</p>${group.rows.map(r=>`<p>${E(bankName(r))} · ${number(r.value)} ${group.metric==='npl_ratio'?tr('শতাংশ পয়েন্ট','percentage points'):'%'} <a class="catalog-source" href="${E(r.source_url)}" target="_blank" rel="noopener noreferrer">${tr('সূত্র ↗','Source ↗')}</a>${r.previous_source_url?` <a class="catalog-source" href="${E(r.previous_source_url)}" target="_blank" rel="noopener noreferrer">${tr('আগের বছরের সূত্র ↗','Previous year ↗')}</a>`:''}</p>`).join('')}</details>`).join(''));
    $('bank-award').innerHTML=data.award?`<p>${tr('স্বীকৃতি: ','Recognition: ')}<a class="catalog-source" href="${E(data.award.source_url)}" target="_blank" rel="noopener noreferrer">${E(bn?data.award.title_bn:data.award.title_en)} ›</a></p>`:'';
    const code=data.status?.code||'no_data';$('card-status-word').textContent=riskWords[code][bn?0:1];
    $('card-status-mark').textContent=({strong:'✓',watch:'⚠',high:'✕',no_data:''})[code];
    $('card-status-panel').dataset.risk=code;$('card-status-panel').classList.toggle('bank-not-rated',code==='no_data');$('card-status-panel').setAttribute('aria-label',tr('ঝুঁকি','Risk'));
    $('bank-risk-heading').textContent=tr('ঝুঁকি','Risk');$('bank-risk-basis').textContent=tr('প্রকাশিত তথ্য অনুযায়ী','Based on published data');
    $('card-status-meaning').textContent=code==='no_data'?tr('এই ব্যাংকের ঝুঁকি এখনো মূল্যায়ন করা হয়নি। নিচে প্রকাশিত রেটিং দেখুন।','This bank’s risk has not been rated. See its published rating below.'):'';
    $('scale-marker').hidden=code==='no_data';['strong','watch','high'].forEach(c=>$('scale-label-'+c).textContent=riskWords[c][bn?0:1]);
    $('reasons-list').querySelectorAll('.reason-source-link').forEach((button,i)=>{button.textContent=tr('সূত্র › ','Source › ')+(bn?data.reasons[i]?.source_label_bn:data.reasons[i]?.source_title);});
    const insured=data.insurance?.covered&&data.insurance?.limit_bdt===200000&&data.insurance?.source_url;
    $('card-insurance-line').hidden=!insured;
    if(insured){$('card-insurance-line').innerHTML=`<p>${tr('প্রতি ব্যাংকে একজন জমাকারীর ২ লাখ টাকা পর্যন্ত আমানত সুরক্ষার নিয়ম আছে, শর্ত প্রযোজ্য।','Deposit protection rules cover up to BDT 200,000 per depositor per bank, subject to conditions.')} <button type="button" class="catalog-source" id="bank-insurance-details">${tr('বিস্তারিত ›','Details ›')}</button></p>`;$('bank-insurance-details').onclick=()=>{const dialog=$('bank-insurance-dialog');$('bank-insurance-full').textContent=bn?data.insurance.text_bn:data.insurance.text_en;$('bank-insurance-source').href=data.insurance.source_url;dialog.showModal();};}
    $('bank-insurance-title').textContent=tr('আমানত সুরক্ষা','Deposit protection');$('bank-insurance-source').textContent=tr('আইনের সূত্র ↗','Legal source ↗');$('bank-insurance-close').textContent=tr('বন্ধ করুন','Close');
    $('bank-insurance-close').onclick=()=>$('bank-insurance-dialog').close();
    $('card-why-heading').textContent=tr('কেন?','Why?');
    $('bank-not-checked').hidden=true;
    const counts=data.section_counts||{},row=(key,b,e)=>`<button type="button" class="catalog-detail-row" data-bank-detail="${key}">${tr(b,e)}${['history','news','announcements','reports','bb-notices'].includes(key)?' ('+digits(counts[key])+')':''} <span aria-hidden="true">›</span></button>`;
    const entries=[['health','আর্থিক অবস্থা','Financial health'],['rating','রেটিং','Rating'],['services','এই ব্যাংকের সেবা ও হার','Services and rates'],['history','জালিয়াতি ও মামলার ইতিহাস','Fraud and legal history'],['news','খবর','News']];
    const extra=[['bb-notices','বাংলাদেশ ব্যাংকের নোটিশ','Bangladesh Bank notices'],['announcements','কোম্পানির ঘোষণা','Company announcements'],['reports','প্রতিবেদন','Reports']].filter(([key])=>counts[key]>0);
    $('bank-detail-links').innerHTML=entries.filter(([key])=>counts[key]>0).map(args=>row(...args)).join('')+(extra.length?`<details class="bank-more"><summary>${tr('আরও তথ্য','More information')}</summary>${extra.map(args=>row(...args)).join('')}</details>`:'')+row('ask','এই ব্যাংক নিয়ে প্রশ্ন করুন','Ask about this bank');
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
      $('sr-announcer').textContent=state.watching?tr('নজরে রাখার তালিকায় যোগ হয়েছে।','Added to your watch list.'):tr('নজরে রাখার তালিকা থেকে সরানো হয়েছে।','Removed from your watch list.');

    }catch{$('sr-announcer').textContent=tr('নজরে রাখার পরিবর্তন সংরক্ষণ করা যায়নি।','Could not save the watch change.');}finally{button.disabled=false;}
  }
  async function showBankDetail(kind) {
    window.IlmaNavigation?.visit({screen:"bank-section",bank:currentBankId,kind});
    $('main-content').scrollTop=0;
    bankPage='detail';detailKind=kind;const root=$('bank-detail-view'), request=++state.epoch;
    $('bank-list-view').hidden=true;$('bank-report-view').hidden=true;root.hidden=false;
    const titles={health:tr('আর্থিক অবস্থা','Financial health'),rating:tr('রেটিং','Rating'),news:tr('খবর','News'),history:tr('জালিয়াতি ও মামলার ইতিহাস','Fraud and legal history'),ask:tr('এই ব্যাংক নিয়ে প্রশ্ন করুন','Ask about this bank')};
    root.innerHTML=`<div class="screen-header">${back('bank-detail-back',tr('রিপোর্ট কার্ড','Report card'))}<h1>${E(titles[kind])}</h1><p>${E(reportCardData?bankName(reportCardData.institution):'')}</p></div><div class="sheet" id="bank-detail-body">${empty(tr('একটু অপেক্ষা করুন…','Please wait…'))}</div>`;
    focusHeading?.(root);$('bank-detail-back').onclick=showReport;const body=$('bank-detail-body');
    if(kind==='ask') {
      body.innerHTML=`<form id="bank-ask-form"><label for="bank-ask-text">${tr('আপনার প্রশ্ন','Your question')}</label><input class="calc-field" id="bank-ask-text" maxlength="1000" required><button class="catalog-action" type="submit">${tr('খুঁজুন','Ask')}</button></form><button class="catalog-action" id="bank-detail-mic" type="button">${tr('প্রশ্ন বলুন','Ask by voice')}</button><div class="catalog-suggestions">${[
        ['এই ব্যাংকের খেলাপি ঋণ কত?','What are this bank’s bad loans?'],['রেটিং কী?','What is the rating?'],['আমার টাকা কতটা সুরক্ষিত?','How much of my deposit is insured?']].map(([b,e])=>`<button class="catalog-detail-row" type="button" data-suggestion="${E(tr(b,e))}">${E(tr(b,e))}</button>`).join('')}</div>`;
      $('bank-ask-form').onsubmit=e=>{e.preventDefault();ask($('bank-ask-text').value,'bank',currentBankId);};
      $('bank-detail-mic').onclick=()=>voice('bank',currentBankId);
      body.querySelectorAll('[data-suggestion]').forEach(b=>b.onclick=()=>ask(b.dataset.suggestion,'bank',currentBankId));return;
    }
    if(['announcements','reports','bb-notices'].includes(kind)){
      root.querySelector('h1').textContent=({announcements:tr('কোম্পানির ঘোষণা','Company announcements'),reports:tr('প্রতিবেদন','Reports'),'bb-notices':tr('বাংলাদেশ ব্যাংকের নোটিশ','Bangladesh Bank notices')})[kind];
      let page=1,group='',publicationRequest=0,lastYear=null;
      body.innerHTML=(kind==='announcements'?`<p class="catalog-note">${tr('ডিএসই-তে ব্যাংকের নিজের ঘোষণা · মূল শিরোনাম ইংরেজিতে','The bank’s own DSE announcements · original titles in English')}</p><div class="bank-publication-filters">${[['','সব','All'],['financials','আর্থিক বিবরণী','Financials'],['dividend','লভ্যাংশ','Dividend'],['credit_rating','রেটিং','Rating'],['board','বোর্ড ও পরিচালক','Board and directors']].map(([key,b,e])=>`<button type="button" data-pub-filter="${key}" aria-pressed="${key===''}">${tr(b,e)}</button>`).join('')}</div>`:'')+'<div id="bank-publication-items"></div>';
      const itemsRoot=$('bank-publication-items');
      async function more(){const turn=++publicationRequest;try{
        const response=await json(`/v1/institutions/${currentBankId}/publications/${kind}?page=${page}${group?'&topic='+group:''}`);if(request!==state.epoch||turn!==publicationRequest)return;
        itemsRoot.querySelector('[data-more]')?.remove();
        const html=response.items.map(row=>{
          const year=row.year||row.date?.slice(0,4),heading=kind==='reports'&&year&&lastYear!==year?`<h2>${digits(year)}</h2>`:'';if(year)lastYear=year;
          return heading+`<article class="catalog-card"><h2>${E(currentLang==='bn'?row.type_label_bn:row.type_label_en)}</h2><p class="catalog-note" lang="en">${E(row.title)}</p>${row.date?`<p>${dateText(row.date)}</p>`:''}<a class="catalog-source" href="${E(row.source_url)}" target="_blank" rel="noopener noreferrer">${tr('সূত্র ↗','Source ↗')}</a></article>`;
        }).join('');itemsRoot.insertAdjacentHTML('beforeend',html);
        if(page*20<response.total){itemsRoot.insertAdjacentHTML('beforeend',`<button type="button" class="catalog-action" data-more>${tr('আরও দেখুন','Show more')}</button>`);itemsRoot.querySelector('[data-more]').onclick=()=>{itemsRoot.querySelector('[data-more]').disabled=true;page++;more();};}
      }catch(e){if(request===state.epoch&&turn===publicationRequest){const previous=itemsRoot.innerHTML;error(itemsRoot,e,()=>{itemsRoot.innerHTML=previous;return more();});}}}
      body.querySelectorAll('[data-pub-filter]').forEach(button=>button.onclick=()=>{group=button.dataset.pubFilter;page=1;lastYear=null;itemsRoot.innerHTML='';body.querySelectorAll('[data-pub-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));more();});
      more();return;
    }
    try {
      const rows=await json(`/v1/institutions/${currentBankId}/${({health:'figures',rating:'ratings',news:'events',history:'history'})[kind]}`);
      if(request!==state.epoch)return;
      if(kind==='history'){renderHistory(body,rows);return;}
      if(!rows.length){body.innerHTML='';return;}
      if(kind==='health') {
        const headings={crar:tr('মূলধন অনুপাত','Capital ratio'),npl_ratio:tr('খেলাপি ঋণ','Bad loans'),net_profit:tr('কর-পরবর্তী মুনাফা','Profit after tax')};
        const explanations={crar:tr('লোকসান সামলাতে ব্যাংকের মূলধনের অনুপাত।','Capital available to absorb losses.'),npl_ratio:tr('যে ঋণের কিস্তি সময়মতো ফেরত আসছে না।','Loans whose installments are not being repaid on time.'),net_profit:tr('কর ও খরচ বাদ দেওয়ার পর মুনাফা।','Profit remaining after expenses and tax.')};
        body.innerHTML=Object.keys(headings).map(metric=>{const records=rows.filter(r=>r.metric===metric),r=records[0];if(!r)return '';
          const heading=metric==='net_profit'&&r.value<0?tr('লোকসান','Loss'):headings[metric];
          const format=r=>r.unit==='ratio'?percent(r.value*100)+'%':number(Math.abs(r.value)/10000000)+' '+tr('কোটি টাকা','crore BDT');
          return `<article class="catalog-card"><h2>${heading}</h2><p class="catalog-value">${format(r)}</p><p>${digits(r.period)}${r.basis==='consolidated'?' · '+tr('গ্রুপ হিসাব','Group accounts'):''}${String(r.basis).endsWith('_calculated')?' · '+tr('নিরীক্ষকের প্রতিবেদন থেকে হিসাব করা','calculated from the auditor’s report'):''}</p><p>${explanations[metric]}</p>${metric==='crar'?`<p>${tr('ন্যূনতম','Minimum')} ${number(r.legal_min*100)}% <small>${tr('(বাংলাদেশ ব্যাংকের নিয়ম)','(Bangladesh Bank rules)')}</small></p>`:''}${metric==='npl_ratio'?`<p>${tr('প্রতি ১০০ টাকার ঋণে','Of each Tk 100 lent, Tk')} ${number(r.value*100)} ${tr('টাকা ফেরত আসছে না।','is not being repaid.')}</p>`:''}${sourceButton(r)}${records[1]?`<p class="bank-trend">${digits(records[1].period)}: ${format(records[1])} → ${digits(r.period)}: ${format(r)} (${r.value===records[1].value?tr('একই','unchanged'):(metric==='net_profit'&&r.value<0&&records[1].value<0?Math.abs(r.value)>Math.abs(records[1].value):r.value>records[1].value)?tr('বেড়েছে','increased'):tr('কমেছে','decreased')})</p>`:''}${records.slice(1).map(old=>`<p class="catalog-note">${digits(old.period)}: ${format(old)} ${sourceButton(old)}</p>`).join('')}</article>`;}).join('');wireSources(body,rows);
      } else if(kind==='rating') {
        body.innerHTML=rows.map(r=>`<article class="catalog-card"><h2>${E(r.agency)} · ${E(r.long_term)}</h2><p>${tr('স্বল্পমেয়াদি','Short term')}: ${E(r.short_term||'—')} · ${tr('পূর্বাভাস','Outlook')}: ${E(outlook(r.outlook))}</p><p>${dateText(r.rated_on)} → ${dateText(r.valid_to)} ${r.expired?tr(' · মেয়াদ শেষ',' · Expired'):''}</p>${r.meaning_bn?`<p>${E(currentLang==='bn'?r.meaning_bn:r.meaning_en)}</p>`:''}<p>${tr('এজেন্সির ঋণ পরিশোধের সক্ষমতা সম্পর্কে মতামত; আমানতের নিশ্চয়তা নয়।','The agency’s opinion of repayment capacity; not a deposit guarantee.')}</p>${sourceButton(r)}</article>`).join('');wireSources(body,rows);
      } else {
        body.innerHTML=rows.map(r=>`<article class="catalog-card"><h2>${E(currentLang==='bn'?r.title_bn:r.title_en)}</h2>${currentLang==='bn'&&!/[\u0980-\u09ff]/.test(r.title_bn)?'<p class="catalog-note">খবরটি ইংরেজিতে</p>':''}<p>${dateText(r.date)}</p><p class="catalog-note">${tr('সংবাদমাধ্যমের খবর','News report')}</p>${r.sources.filter(s=>/^https?:\/\//.test(s.source_url)).map(s=>`<a class="catalog-source" href="${E(s.source_url)}" target="_blank" rel="noopener noreferrer">${tr('মূল সূত্র ↗','Original source ↗')}</a>`).join('')}</article>`).join('');
      }
    }catch(e){if(request===state.epoch)error(body,e,()=>showBankDetail(kind));}
  }

  function renderHistory(body,data) {
    const bn=currentLang==='bn', items=data.items||[];
    body.innerHTML=`<p class="catalog-note">${tr('প্রকাশিত খবর ও সরকারি নথি থেকে। পুরোনো ঘটনা বর্তমান ঝুঁকির মাপ নয়।','From published news and official documents. Past incidents are not a measure of current risk.')}</p>${items.length?`<label for="incident-filter">${tr('ঘটনার ধরন','Incident type')}</label><select class="calc-field" id="incident-filter"><option value="">${tr('সব','All')}</option>${[...new Set(items.map(r=>r.kind))].map(kind=>{const row=items.find(r=>r.kind===kind);return `<option value="${E(kind)}">${E(bn?row.type_label_bn:row.type_label_en)}</option>`;}).join('')}</select><div id="incident-rows"></div>`:''}`;
    if(!items.length)return;
    function render(){
      const sources=[];
      $('incident-rows').innerHTML=items.filter(row=>!$('incident-filter').value||row.kind===$('incident-filter').value).map(row=>{
        const proof=row.sources.map(source=>({...source,fact_id:source.source_id}));sources.push(...proof);
        return `<article class="catalog-card"><h2>${E(bn?row.title_bn:row.title_en)}</h2><p>${row.official?tr('সরকারি নথি','Official document'):tr('সংবাদমাধ্যমের খবর','News report')}</p><p><strong>${E(bn?row.status_label_bn:row.status_label_en)}</strong> · ${dateText(row.last_update_on)}</p>${new Date(row.first_reported_on)<new Date(new Date().setFullYear(new Date().getFullYear()-3))?`<span class="bank-meta-chip">${tr('পুরোনো ঘটনা','Older incident')}</span>`:''}<p>${tr('প্রথম প্রকাশ','First reported')}: ${dateText(row.first_reported_on)}</p><ol>${row.changes.map(change=>`<li>${dateText(change.changed_on)} · ${E(bn?change.status_label_bn:change.status_label_en)}</li>`).join('')}</ol>${proof.map(source=>sourceButton(source)).join('')}</article>`;
      }).join('')||empty();wireSources($('incident-rows'),sources);
    }
    $('incident-filter').onchange=render;render();
  }

  window.IlmaBank={async restore(route,isCurrent=()=>true){if(route.screen==='banks')return showBankList();await showReport();if(!isCurrent())return;if(route.screen==='bank-section')return showBankDetail(route.kind);},reportReady,toggleWatch,listenReport,enter(){currentBankId?showReport():showBankList();},relocalize(){if(bankPage==='list')renderBankList();else if(bankPage==='detail')showBankDetail(detailKind);else if(reportCardData)reportReady(reportCardData);}};
})();
