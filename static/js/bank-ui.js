/* Bank list, report and sourced section screens. */
(()=>{
  const {$,E,tr,digits,dateText,number,label,outlook,percent,bankName,statusChip,bankNames,productText,conditionText,offerStatus,empty,back,json,sourceButton,wireSources,voice,ask,error,state}=window.IlmaCatalogCommon;
  let banks=[],bankPage='list',detailKind='health';
  const openBankServices=(...args)=>window.IlmaServices.openBankServices(...args);
  function reportView(show) {
    $('main-content').scrollTop=0;
    $('bank-list-view').hidden=show;
    $('bank-report-view').hidden=!show;
    $('bank-detail-view').hidden=true;
  }
  async function showBankList() {
    ++reportRequest; reportCardData=null;bankPage='list'; currentBankId=null; reportView(false); $('bank-list-view').hidden=false;
    const root=$('bank-list-view'), request=++state.epoch;
    root.innerHTML=empty(tr('একটু অপেক্ষা করুন…','Please wait…'));
    try { banks=await json('/v1/institutions?list=demo'); if(request!==state.epoch)return; renderBankList(); }
    catch(e){if(request===state.epoch)error(root,e);}
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
  function showReport() { ++state.epoch; bankPage='report';reportView(true);$('btn-watch-bank').setAttribute('aria-pressed','false');$('btn-watch-bank').disabled=true;loadReportCard(currentBankId); }
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
    bankPage='detail';detailKind=kind;const root=$('bank-detail-view'), request=++state.epoch;
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
        const response=await json(`/v1/institutions/${currentBankId}/publications/${kind}?page=${page}`);if(request!==state.epoch)return;
        body.querySelector('[data-more]')?.remove();
        const html=response.items.map(row=>window.publicationHTML(row,kind==='announcements'?tr('ডিএসই-তে ব্যাংকের নিজের ঘোষণা','The bank’s own DSE announcement'):kind==='reports'?tr('ব্যাংকের প্রকাশিত প্রতিবেদন','Bank-published report'):tr('বাংলাদেশ ব্যাংকের নোটিশ','Bangladesh Bank notice'))).join('');
        body.insertAdjacentHTML('beforeend',html||empty());
        if(page*20<response.total){body.insertAdjacentHTML('beforeend',`<button type="button" class="catalog-action" data-more>${tr('আরও দেখুন','Show more')}</button>`);body.querySelector('[data-more]').onclick=()=>{body.querySelector('[data-more]').disabled=true;page++;more();};}
      }catch(e){if(request===state.epoch)error(body,e);}}
      more();return;
    }
    try {
      const rows=await json(`/v1/institutions/${currentBankId}/${({health:'figures',rating:'ratings',news:'events',history:'history'})[kind]}`);
      if(request!==state.epoch)return;
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
    }catch(e){if(request===state.epoch)error(body,e);}
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

  window.IlmaBank={reportReady,toggleWatch,enter(){currentBankId?showReport():showBankList();},relocalize(){if(bankPage==='list')renderBankList();else if(bankPage==='detail')showBankDetail(detailKind);else if(reportCardData)reportReady(reportCardData);}};
})();
