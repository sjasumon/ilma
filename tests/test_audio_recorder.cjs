const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function createRecorder({ permissionError = null, stopStalls = false } = {}) {
  const intervals = new Map(), timeouts = new Map();
  let now = 0, level = .1, next = 0, tracksStopped = 0;
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
    navigator: { mediaDevices: { async getUserMedia() {
      if (permissionError) throw Object.assign(Error('Permission denied'), { name: permissionError });
      return { getTracks: () => [{ stop() { tracksStopped++; } }] };
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
    stopped: () => tracksStopped, timers: () => intervals.size + timeouts.size
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
  assert.ok(app.stopped());
  assert.equal(app.timers(), 0);

  const noSpeech = createRecorder();
  let error;
  await noSpeech.recorder.start({ onComplete() {}, onError: code => error = code });
  noSpeech.sample(6100, 0);
  assert.equal(error, 'no-speech');
  assert.ok(noSpeech.stopped());
  assert.equal(noSpeech.timers(), 0);

  const cap = createRecorder(); let capped = 0;
  await cap.recorder.start({ onComplete: () => capped++, onError() {} });
  cap.limit(); assert.equal(capped, 1); cap.recorder.cancel(); assert.ok(cap.stopped());
  const blocked = createRecorder({ permissionError: 'NotAllowedError' });
  await assert.rejects(blocked.recorder.start({ onComplete() {}, onError() {} }), { name: 'NotAllowedError' });
  assert.equal(blocked.recorder.context.state, 'closed');
  const stalled = createRecorder({stopStalls:true});
  await stalled.recorder.start({onComplete(){},onError(){}});
  const rejected = assert.rejects(stalled.recorder.finish(), /recording_finalize_timeout/);
  stalled.limit();
  await rejected;
  assert.equal(stalled.timers(), 0);
  assert.ok(stalled.stopped());
  const cancelled = createRecorder({stopStalls:true});
  await cancelled.recorder.start({onComplete(){},onError(){}});
  const cancelledFinish = assert.rejects(cancelled.recorder.finish(), /cancelled/);
  cancelled.recorder.cancel();
  await cancelledFinish;
  assert.equal(cancelled.timers(), 0);
  console.log('Audio recorder passed: raw compressed recording, configurable silence detection, 15-second timer, no-speech, track/timer cleanup and permission denial');
})().catch(error => { console.error(error); process.exitCode = 1; });
