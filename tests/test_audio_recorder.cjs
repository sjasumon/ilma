const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function createRecorder({ permissionError = null, stopStalls = false, permissionState = "granted", echoCancellation = true } = {}) {
  const intervals = new Map(), timeouts = new Map();
  let now = 0, level = .1, next = 0, tracksStopped = 0, requests = 0;
  const decoded = { length: 48000, sampleRate: 48000, numberOfChannels: 1, getChannelData: () => new Float32Array(48000).fill(.1) };
  class AudioContext {
    state = 'running'; destination = {};
    resume() { return Promise.resolve(); }
    close() { this.state = 'closed'; return Promise.resolve(); }
    decodeAudioData() { return Promise.resolve(decoded); }
    createMediaStreamSource() { return { connect() {} }; }
    createAnalyser() { return { fftSize: 1024, getFloatTimeDomainData(samples) { samples.fill(level); }, connect(node) { return node; } }; }
    createGain() { return { gain: {}, connect() {} }; }
  }
  class MediaRecorder {
    static isTypeSupported() { return true; }
    mimeType = 'audio/webm'; state = 'inactive';
    start() { this.state = 'recording'; }
    stop() { this.state = 'inactive'; this.ondataavailable({ data: new Blob(['encoded recording']) }); if (!stopStalls) this.onstop(); }
  }
  const context = vm.createContext({
    Blob, Date: { now: () => now },
    navigator: { permissions: {async query(){return {state:permissionState}}}, mediaDevices: { async getUserMedia() {
      requests++;
      if (permissionError) throw Object.assign(Error('Permission denied'), { name: permissionError });
      const track={stop(){tracksStopped++},getSettings(){return {echoCancellation}}};return {getTracks:()=>[track],getAudioTracks:()=>[track]};
    } } },
    window: { AudioContext, MediaRecorder },
    setInterval(fn) { intervals.set(++next, fn); return next; }, clearInterval(id) { intervals.delete(id); },
    setTimeout(fn) { timeouts.set(++next, fn); return next; }, clearTimeout(id) { timeouts.delete(id); }
  });
  vm.runInContext(fs.readFileSync('static/js/voice-recorder.js', 'utf8'), context);
  return {
    context, decoded, recorder: new context.window.IlmaVoiceRecorder(),
    sample(time, amplitude) { now = time; level = amplitude; for (const fn of [...intervals.values()]) fn(); },
    limit() { for (const fn of [...timeouts.values()]) fn(); },
    stopped: () => tracksStopped, requests: () => requests, timers: () => intervals.size + timeouts.size
  };
}
(async () => {
  const app = createRecorder();
  let completed = 0;
  await app.recorder.start({ onComplete: () => completed++, onError: code => { throw Error(code); } });
  app.sample(100, 0); app.sample(400, .1); app.sample(1700, 0); assert.equal(completed, 0);
  app.sample(2000, 0); assert.equal(completed, 1);
  const recorded = await app.recorder.finish();
  assert.equal(recorded.type, 'audio/webm');
  assert.equal(app.stopped(), 0, 'Keep the microphone for the visit');
  assert.equal(app.timers(), 0);
  const again = new app.context.window.IlmaVoiceRecorder();
  await again.start({ onComplete() {}, onError() {} }); again.cancel();
  assert.equal(app.requests(), 1, 'Ask for the microphone once per visit');
  app.context.window.IlmaMicrophone.release(); assert.ok(app.stopped());

  const brief=createRecorder();let briefCompleted=0,briefError;
  await brief.recorder.start({onComplete(){briefCompleted++},onError(code){briefError=code}});
  brief.sample(100,.08);brief.sample(200,0);brief.sample(1700,0);
  assert.equal(briefCompleted,1,'A short reply during calibration must be retained');assert.equal(briefError,undefined);brief.recorder.cancel();
  const noisy=createRecorder();let warnings=0;await noisy.recorder.start({onComplete(){},onError(){},onNoise(){warnings++}});noisy.sample(100,.06);noisy.sample(200,.06);noisy.sample(400,.06);assert.equal(warnings,1,'Early-reply capture must preserve the ambient-noise warning');noisy.recorder.cancel();
  const barge=createRecorder();let transferred=null;
  const monitor=new barge.context.window.IlmaBargeMonitor();await monitor.start(stream=>transferred=stream);
  for(let i=0;i<10;i++)barge.sample(i*50,0);
  for(let i=0;i<3;i++)barge.sample(550+i*50,.1);
  assert.equal(transferred,null,'Require sustained voice, not one sound');
  barge.sample(700,.1);assert.ok(transferred);assert.equal(barge.stopped(),0,'Transfer microphone without stopping it');assert.equal(barge.timers(),0);
  await barge.recorder.start({stream:transferred,onComplete(){},onError(){}});barge.recorder.cancel();assert.ok(barge.stopped());
  const deniedMonitor=createRecorder({permissionState:'prompt'});await new deniedMonitor.context.window.IlmaBargeMonitor().start(()=>assert.fail());assert.equal(deniedMonitor.timers(),0,'Never ask for microphone permission during speech');
  const noEcho=createRecorder({echoCancellation:false});await new noEcho.context.window.IlmaBargeMonitor().start(()=>assert.fail());assert.ok(noEcho.stopped());assert.equal(noEcho.timers(),0);
  const cancelledMonitor=createRecorder();const pending=new cancelledMonitor.context.window.IlmaBargeMonitor();const starting=pending.start(()=>assert.fail());pending.cancel();await starting;assert.equal(cancelledMonitor.timers(),0);
  const noSpeech = createRecorder();
  let error;
  await noSpeech.recorder.start({ onComplete() {}, onError: code => error = code });
  noSpeech.sample(6100, 0);
  assert.equal(error, 'no-speech');
  noSpeech.context.window.IlmaMicrophone.release(); assert.ok(noSpeech.stopped());
  assert.equal(noSpeech.timers(), 0);

  const patient=createRecorder();let patientError;
  await patient.recorder.start({noSpeechMs:8000,maxMs:15000,onComplete(){},onError(code){patientError=code}});
  patient.sample(6100,0);assert.equal(patientError,undefined);patient.sample(8100,0);assert.equal(patientError,'no-speech');
  const cap = createRecorder(); let capped = 0;
  await cap.recorder.start({ onComplete: () => capped++, onError() {} });
  cap.sample(400,.1);cap.limit(); assert.equal(capped, 1); cap.recorder.cancel(); cap.context.window.IlmaMicrophone.release(); assert.ok(cap.stopped());
  const guidedQuiet = createRecorder(); let guidedError;
  await guidedQuiet.recorder.start({ maxMs: 6000, onComplete() { throw Error('silent IVR audio must not upload'); }, onError: code => guidedError = code });
  guidedQuiet.limit(); assert.equal(guidedError, 'no-speech'); guidedQuiet.context.window.IlmaMicrophone.release(); assert.ok(guidedQuiet.stopped());
  const guidedSpeech = createRecorder(); let guidedCompleted = 0;
  await guidedSpeech.recorder.start({ maxMs: 6000, onComplete() { guidedCompleted++; }, onError(code) { throw Error(code); } });
  guidedSpeech.sample(400, .1); guidedSpeech.limit(); assert.equal(guidedCompleted, 1); guidedSpeech.recorder.cancel();
  const blocked = createRecorder({ permissionError: 'NotAllowedError' });
  await assert.rejects(blocked.recorder.start({ onComplete() {}, onError() {} }), { name: 'NotAllowedError' });
  assert.equal(blocked.recorder.context.state, 'running');
  const stalled = createRecorder({stopStalls:true});
  await stalled.recorder.start({onComplete(){},onError(){}});
  const rejected = assert.rejects(stalled.recorder.finish(), /recording_finalize_timeout/);
  stalled.limit();
  await rejected;
  assert.equal(stalled.timers(), 0);
  stalled.context.window.IlmaMicrophone.release(); assert.ok(stalled.stopped());
  const cancelled = createRecorder({stopStalls:true});
  await cancelled.recorder.start({onComplete(){},onError(){}});
  const cancelledFinish = assert.rejects(cancelled.recorder.finish(), /cancelled/);
  cancelled.recorder.cancel();
  await cancelledFinish;
  assert.equal(cancelled.timers(), 0);
  const device=createRecorder();const closes=(userAgent,platform='',maxTouchPoints=0)=>{Object.assign(device.context.navigator,{userAgent,platform,maxTouchPoints});return device.context.window.IlmaMicrophone.closesForPlayback()};
  assert.equal(closes('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)'),true,'iPhone closes the mic for playback');
  assert.equal(closes('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)','MacIntel',5),true,'iPad in desktop mode closes the mic');
  assert.equal(closes('Mozilla/5.0 (Linux; Android 14; Pixel 8)','Linux armv8l',5),false,'Android keeps the mic behaviour');
  assert.equal(closes('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)','MacIntel',0),false,'A Mac keeps the mic behaviour');
  const iosMode=createRecorder();const order=[];
  iosMode.context.navigator.userAgent='iPhone';
  const shared=new iosMode.context.window.AudioContext();shared.resume=()=>{order.push('resume');return Promise.resolve()};
  iosMode.context.window.IlmaAudioSession={forRecording(){order.push('recording-mode')},getContext(){return shared}};
  await iosMode.recorder.start({onComplete(){},onError(){}});
  assert.equal(order[0],'recording-mode','iOS must select recording mode before resuming its context');
  iosMode.recorder.cancel();
  console.log('Audio recorder passed: raw compressed recording, configurable silence detection, 15-second timer, no-speech, one microphone grant per visit, track/timer cleanup and permission denial');
})().catch(error => { console.error(error); process.exitCode = 1; });
