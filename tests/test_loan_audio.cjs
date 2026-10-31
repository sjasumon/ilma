// Synthetic state transitions: edited borrower inputs cannot play the saved default.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const nodes = new Map();
const node = id => {
  if (!nodes.has(id)) nodes.set(id, {textContent:'', innerHTML:'', hidden:true, value:'', dataset:{}, setAttribute(){}, querySelectorAll(){return [];}});
  return nodes.get(id);
};
const years = [1, 5, 20].map(y => ({dataset:{loanYears:String(y)}, setAttribute(){}}));
let played = 0, stopped = 0;
const common = {$:node, E:String, tr:(bn,en)=>bn, digits:String, dateText:String, number:String, bankNames:()=>'', bankName:()=>'', back:()=>'',offlineNote:()=>''};
const context = vm.createContext({
  window:{IlmaCatalogCommon:common}, document:{querySelectorAll:selector=>selector==='[data-loan-years]'?years:[]},
  currentLang:'bn', suppressReadoutClick:false, playbackRequest:0,
  stopAudio(){stopped++;}, playVoiceAudio(){played++; return true;},
});
vm.runInContext(fs.readFileSync('static/js/loan-ui.js', 'utf8'), context);
const loans = context.window.IlmaLoans;
loans.mount({choice:{product_type:'home_loan'}, rows:[], readout:{text:'Approved synthetic example', example_amount:2000000, example_years:20, audio_url:'/static/audio/services/bn/loan_home.mp3?v=aaaaaaaaaaaaaaaa'}}, {});
node('loan-listen').onclick();
assert.equal(played,1,'Default click must initiate playback synchronously');
assert.equal(node('loan-narration').textContent,'Approved synthetic example');
const edit = value => node('loan-amount').oninput({target:{value,setAttribute(){}}});
edit('4000000');
assert.equal(node('loan-narration').hidden,false);
node('loan-listen').onclick(); assert.equal(played,1,'Edited amount must suppress playback');
edit('2000000');
years[1].onclick(); node('loan-listen').onclick(); assert.equal(played,1,'Edited years must suppress playback');
years[2].onclick(); node('loan-listen').onclick(); assert.equal(played,2,'Restored default can play again');
edit('0'); node('loan-listen').onclick(); assert.equal(played,2,'Invalid amount must suppress playback');
assert.ok(stopped>=5,'Editing inputs must interrupt playback');
console.log('Loan default example audio guards passed');
