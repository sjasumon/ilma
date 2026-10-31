/* Public routes only. Calculator values and searches stay in module memory. */
(()=>{
  const allowed=new Set(['screen','bank','kind','id','product_type','item','audience','basis','network','tier','attribute','compare_by','tenor_months']);
  let restoring=0,serial=0,turn=0,activeEntry=Number(history.state?.entry)||0;
  const positions=new Map();
  const clean=route=>Object.fromEntries(Object.entries(route).filter(([k,v])=>allowed.has(k)&&v!=null&&/^[a-zA-Z0-9_ .:-]{1,160}$/.test(String(v))).map(([k,v])=>[k,String(v)]));
  const initial=clean(Object.fromEntries(new URLSearchParams(location.hash.slice(1))));
  function save(){if(history.state?.ilma)positions.set(activeEntry,document.getElementById('main-content').scrollTop);}
  function visit(route){
    if(restoring)return;
    ++turn;route=clean(route);
    if(JSON.stringify(history.state?.route)===JSON.stringify(route))return;
    save();const depth=(history.state?.ilma?history.state.depth:0)+1;
    activeEntry=++serial;history.pushState({ilma:true,entry:activeEntry,depth,route},'', '#'+new URLSearchParams(route));
  }
  async function restore(entry){
    const request=++turn;let pending;
    // Suppress only the synchronous route dispatch. A slow request must never
    // prevent a later user action from recording its own navigation.
    restoring++;
    try{
      const route=entry.route||{},screen=route.screen;
      if(['banks','report','bank-section'].includes(screen)){
        currentBankId=screen==='banks'?null:Number(route.bank);switchTab('detail',false,true);
        pending=window.IlmaBank.restore(route,()=>request===turn);
      }else if(['services','compare','offer','bank-services','account-bank'].includes(screen)){
        switchTab('services',false,true);pending=window.IlmaServices.restore(route);
      }else switchTab(screen==='news'?'news':'home',false,true);
    }finally{restoring--;}
    await pending;
    if(request===turn)document.getElementById('main-content').scrollTop=positions.get(entry.entry)||0;
  }
  function update(changes){if(restoring||!history.state?.ilma)return;const entry={...history.state,route:clean({...history.state.route,...changes})};history.replaceState(entry,'','#'+new URLSearchParams(entry.route));}
  window.IlmaNavigation={visit,update,get restoring(){return restoring>0;}};
  serial=Number(history.state?.entry)||0;
  if(!history.state?.ilma)history.replaceState({ilma:true,entry:serial,depth:0,route:initial.screen?initial:{screen:'home'}},'',location.href);
  window.addEventListener('popstate',event=>{save();if(event.state?.ilma){activeEntry=event.state.entry;void restore(event.state);}});
  // Native Back and the app's Back controls follow the same entry sequence.
  document.addEventListener('click',event=>{
    if(event.target.closest('#services-home-back'))return;
    if(!event.target.closest('.catalog-back, #bank-list-back')||!history.state?.depth)return;
    event.preventDefault();event.stopImmediatePropagation();save();history.back();
  },true);
  window.addEventListener('hashchange',()=>{
    const route=clean(Object.fromEntries(new URLSearchParams(location.hash.slice(1))));
    if(!route.screen||JSON.stringify(history.state?.route)===JSON.stringify(route))return;
    const entry={ilma:true,entry:++serial,depth:0,route};activeEntry=entry.entry;history.replaceState(entry,'',location.href);void restore(entry);
  });
  document.addEventListener('DOMContentLoaded',()=>{if(initial.screen)void restore(history.state);});
})();
