// Exercise real screen modules and app playback/reset with a fake media element.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { createApp } = require('./frontend_harness.cjs');

function load(app, name) { vm.runInContext(fs.readFileSync('static/js/'+name+'.js','utf8'),app.context); }
function fixture(language) {
  const app=createApp({savedSettings:{language,micExplained:false}});
  app.context.URLSearchParams=URLSearchParams;
  for(const name of ['catalog-common','loan-ui','deposit-ui','account-ui','bank-ui','services-ui','bank-services-ui'])load(app,name);
  let played=0;
  app.node('ilma-player').play=()=>{played++;return Promise.resolve();};
  app.run("currentTab='services'");
  return {app,played:()=>played};
}
const text='পরীক্ষার অনুমোদিত বাংলা পাঠ।\n\nএকই পাঠ অপরিবর্তিত।';
const url='/static/audio/services/bn/loan_home.mp3?v=aaaaaaaaaaaaaaaa';
function assertClip(app,id,transcript,played,count,language) {
  app.node(id).onclick();
  assert.equal(played(),count,'play must be called synchronously during the click');
  assert.equal(app.node(transcript).textContent,text,'show the exact approved text');
  assert.equal(app.node(transcript).lang,'bn');
  assert.equal(app.node(id).textContent,language==='bn'?'থামুন':'Stop');
  app.run('stopAudio()');
  if(language==='en')assert.match(app.node(id).textContent,/Bangla/);
}
(async()=>{
  for(const language of ['bn','en']) {
    const {app,played}=fixture(language),api=app.context.window;
    api.IlmaLoans.mount({choice:{product_type:'home_loan'},rows:[],readout:{text,audio_url:url,example_amount:2000000,example_years:20}},{});
    assertClip(app,'loan-listen','loan-narration',played,1,language);
    app.node('loan-amount').oninput({target:{value:'4000000',setAttribute(){}}});
    const label=app.node('loan-listen').textContent;
    app.node('loan-listen').onclick();assert.equal(played(),1);
    app.run('stopAudio()');assert.equal(app.node('loan-listen').textContent,label,'Stop must retain the edited-example label');
    api.IlmaLoans.mount({choice:{product_type:'home_loan'},rows:[],readout:{text,audio_url:null,example_amount:2000000,example_years:20}},{});
    app.node('loan-amount').oninput({target:{value:'2000000',setAttribute(){}}});
    app.node('loan-listen').onclick();assert.equal(played(),1);assert.equal(app.node('loan-audio-error').hidden,true,'Read-only example should not produce a playback error');
    api.IlmaDeposits.mount({choice:{product_type:'fdr'},catalog_banks:[],insurance:null,readouts:{'fdr-12-all':{text,audio_url:url,example_amount:100000,example_months:12}}},{});
    assertClip(app,'deposit-listen','deposit-narration',played,2,language);
    app.node('deposit-amount').oninput({target:{value:'200000',setAttribute(){}}});
    const depositLabel=app.node('deposit-listen').textContent;
    app.node('deposit-listen').onclick();assert.equal(played(),2);
    app.run('stopAudio()');assert.equal(app.node('deposit-listen').textContent,depositLabel);
    api.IlmaAccounts.mount({choice:{item:'savings',audience:'all'},banks:[],readouts:{'savings-all':{text,audio_url:url,example_balance:100000}}},{});
    assertClip(app,'account-listen','account-narration',played,3,language);
    app.node('account-balance').oninput({target:{value:'200000',setAttribute(){}}});
    const accountLabel=app.node('account-listen').textContent;
    app.node('account-listen').onclick();assert.equal(played(),3);
    app.run('stopAudio()');assert.equal(app.node('account-listen').textContent,accountLabel);
    app.context.sample={text,audio_url:url};app.run("reportCardData={readout:sample};currentTab='detail'");
    api.IlmaBank.listenReport();assert.equal(played(),4);
    assert.equal(app.node('bank-report-transcript').textContent,text);
    assert.equal(app.node('bank-report-transcript').lang,'bn');
    app.run('stopAudio()');if(language==='en')assert.match(app.node('lbl-listen-rpt').textContent,/Bangla/);
    const cardURL='/static/audio/services/bn/card-visa-gold-annual-fee.mp3?v=aaaaaaaaaaaaaaaa';
    app.context.fetch=async path=>({ok:true,headers:{get:()=>null},json:async()=>path.includes('audio-manifest')?{clips:{synthetic:{reviewed:true,file:'bn/card-visa-gold-annual-fee.mp3',audio_sha256:'a'.repeat(64),text}}}:path.includes('categories')?[{category:'card',choices:[['Visa','Gold']]}]:{choice:{product_type:'card',attribute:'annual_fee'},rows:[],readout:{text,audio_url:cardURL}}});
    await api.IlmaServices.enter();
    await api.IlmaServices.openComparison({product_type:'card',network:'Visa',tier:'Gold'});
    assertClip(app,'compare-listen','comparison-narration',played,5,language);
    assert.equal(app.node('comparison-audio-error').hidden,true);
    console.log('Saved audio language and default-example guards passed:',language);
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
