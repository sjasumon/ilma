const assert = require('node:assert/strict');
const { GuidedVoice, IVR_STEPS } = require('../static/js/ivr.js');
function fixture() {
  let time = 0, serial = 0, mic = false, promptEnd;
  const timers = new Map(), calls = [];
  const clock = { now: () => time, setTimeout(fn, ms) { timers.set(++serial,{fn,at:time+ms}); return serial; }, clearTimeout(id) { timers.delete(id); } };
  const a = {
    cancel() { mic = false; }, render(id) { calls.push(['render',id]); }, announce() {},
    prompt(id) { calls.push(['prompt',id]); return new Promise(resolve => { promptEnd = resolve; }); },
    async listen(id) { calls.push(['listen',id]); mic = true; }, recording: () => mic,
    assistive: () => false, interrupt() { calls.push(['interrupt']); if (promptEnd) { const end=promptEnd;promptEnd=null;end(false); } },
    finish() { mic=false;calls.push(['finish']); }, echo(n,id) { calls.push(['echo',n,id]); },
    action(action) { calls.push(['action',action]); }, read(kind) { calls.push(['read',kind]); }, exit() { calls.push(['home']); }
  };
  const flow = new GuidedVoice(a,clock);
  const settle = async () => { for(let i=0;i<8;i++) await Promise.resolve(); };
  return {flow,a,calls,timers,settle,
    async endPrompt(heard=true) { const end=promptEnd;promptEnd=null;end(heard);await settle(); },
    async advance(ms) { time+=ms;for(const [id,t] of [...timers]) if(t.at<=time) { timers.delete(id); t.fn(); } await settle(); },
    count: name => calls.filter(c=>c[0]===name).length
  };
}
(async()=>{
  for(const step of Object.values(IVR_STEPS)) for(const key of ['id','clip','onTap1','onTap2','words','onSilence']) assert.ok(key in step);
  const one=fixture();one.flow.enter('menu');await one.endPrompt(false);
  one.flow.tap({detail:1});await one.advance(449);assert.equal(one.count('action'),0);
  await one.advance(1);assert.deepEqual(one.calls.at(-1),['action','bank']);
  const two=fixture();two.flow.enter('menu');await two.endPrompt(false);
  two.flow.tap({detail:1});await two.advance(200);two.flow.tap({detail:2});await two.settle();
  assert.deepEqual(two.calls.at(-1),['action','services']);await two.advance(450);assert.equal(two.count('action'),1);
  const keyboard=fixture();keyboard.flow.enter('menu');await keyboard.endPrompt(false);
  keyboard.flow.tap({detail:0});await keyboard.settle();assert.deepEqual(keyboard.calls.at(-1),['action','bank']);
  const talking=fixture();talking.flow.enter('menu');assert.equal(talking.count('listen'),0);
  await talking.advance(20000);assert.equal(talking.count('listen'),0,'never record over a prompt');
  await talking.endPrompt();assert.equal(talking.count('listen'),1);
  talking.flow.tap({detail:1});await talking.advance(200);talking.flow.tap({detail:2});
  assert.equal(talking.count('finish'),1);assert.equal(talking.count('action'),0,'recording pair cannot select choice 2');
  const silence=fixture();silence.flow.enter('menu');await silence.endPrompt();silence.a.cancel();silence.flow.silent();
  await silence.advance(7999);assert.equal(silence.count('prompt'),1);
  await silence.advance(1);assert.equal(silence.count('prompt'),2);await silence.endPrompt();silence.a.cancel();silence.flow.silent();
  await silence.advance(60000);assert.equal(silence.count('prompt'),2,'re-ask once, then quiet');
  const interrupt=fixture();interrupt.flow.enter('menu');interrupt.flow.tap({detail:1});await interrupt.advance(450);
  assert.deepEqual(interrupt.calls.at(-1),['action','bank']);assert.equal(interrupt.count('listen'),0,'interrupt also counts as choice');
  const skip=fixture();skip.flow.enter('name');skip.flow.tap({detail:1});skip.flow.skip();await skip.advance(60000);
  assert.equal(skip.flow.active,false);assert.equal(skip.count('home'),1);assert.equal(skip.count('listen'),0);assert.equal(skip.count('action'),0);
  const report=fixture();report.flow.enter('report');report.flow.tap({detail:1});await report.settle();
  assert.equal(report.flow.id,'next','any report tap stops playback and advances');
  const words=fixture();words.flow.enter('language');await words.endPrompt(false);await words.flow.command('two');
  assert.deepEqual(words.calls.at(-1),['action','en']);
  const {createApp}=require('./frontend_harness.cjs');
  function settingsApp(options={}) {
    const app=createApp(options);
    app.run(`window.IlmaGuidedVoice=class {
      constructor(adapter){this.a=adapter;this.active=false;this.epoch=0;this.entered=[];}
      clear(){}
      enter(id){this.active=true;this.id=id;this.entered.push(id);}
      skip(){this.active=false;this.a.exit();}
    };setupGuidedVoice();`);
    return app;
  }
  const fresh=settingsApp();
  assert.equal(fresh.run('appSettings.voiceonly'),false);
  assert.equal(fresh.run('ivr.active'),false,'first-use flag must not enable guided mode');
  fresh.run('startGuidedVoice()');assert.equal(fresh.run('ivr.active'),false,'disabled mode cannot be started implicitly');
  await fresh.fire('settings-btn','click');fresh.node('settings-voiceonly').checked=true;
  await fresh.fire('settings-voiceonly','change');await fresh.fire('settings-close','click');
  assert.equal(fresh.run('ivr.active'),true);assert.equal(fresh.run('ivr.id'),'open');
  assert.equal(JSON.parse(fresh.stored.get('ilma-settings')).voiceonly,true);
  fresh.run("ivr.enter('menu')");await fresh.fire('settings-btn','click');await fresh.fire('settings-close','click');
  assert.equal(fresh.run('ivr.id'),'menu','unrelated settings must resume the current step');
  await fresh.fire('settings-btn','click');fresh.node('settings-voiceonly').checked=false;
  await fresh.fire('settings-voiceonly','change');await fresh.fire('settings-close','click');
  assert.equal(fresh.run('ivr.active'),false);assert.equal(fresh.run('currentTab'),'home');
  const restored=settingsApp({savedSettings:JSON.parse(fresh.stored.get('ilma-settings'))});
  assert.equal(restored.run('ivr.active'),false,'disabled setting survives reload');
  const enabled=settingsApp({savedSettings:{voiceonly:true,ivrFinished:false}});
  assert.equal(enabled.run('ivr.active'),true,'explicitly saved enabled mode starts on load');
  const blocked=settingsApp({storageBlocked:true});assert.equal(blocked.run('ivr.active'),false);
  console.log('Guided voice passed: choice timing, native activation, mic pair isolation, prompt sequencing, one silence retry, interruption, skip and spoken choices');
})().catch(error=>{console.error(error);process.exitCode=1;});
