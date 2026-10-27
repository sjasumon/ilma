const assert = require('node:assert/strict');
const { createApp } = require('./frontend_harness.cjs');
function response(events) {
  // Split across UTF-8 code points and SSE frame boundaries to exercise buffering.
  const bytes = new TextEncoder().encode(events.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`).join(''));
  let offset = 0;
  return { ok: true, body: { getReader: () => ({
    async read() { if (offset >= bytes.length) return { done: true }; const value = bytes.slice(offset, offset + 7); offset += 7; return { value, done: false }; },
    async cancel() {}
  }) } };
}
function voiceApp(options = {}) {
  const app = createApp(options);
  app.context.fetch = async (url, request) => {
    assert.equal(url, '/v1/voice');
    assert.equal(request.method, 'POST');
    const context = JSON.parse(request.body.get('context'));
    assert.equal(context.ui_lang, app.document.documentElement.lang);
    assert.equal(request.body.get('audio').type, 'audio/webm');
    return response([
      ['transcript', { text: 'পূবালী ব্যাংক', language: 'bn' }],
      ['match', { institution_ids: [102], confidence: 1 }],
      ['result', { type: 'report_card', institution_id: 102, text: 'পূবালী ব্যাংকের তথ্য', language: 'bn' }]
    ]);
  };
  app.run('openBank = id => { globalThis.openedBank = id; };');
  return app;
}
(async () => {
  const permission = voiceApp({ savedSettings: { micExplained: false } });
  await permission.fire('home-tap-target', 'click');
  assert.equal(permission.node('mic-permission-dialog').open, true);
  assert.equal(permission.recorders.length, 0);
  await permission.fire('mic-permission-allow', 'click');
  assert.equal(permission.run('isListening'), true);

  const unsupported = voiceApp({ recordingSupported: false });
  await unsupported.fire('home-tap-target', 'click');
  assert.equal(unsupported.run('currentTab'), 'home');
  assert.equal(unsupported.node('voice-text-form').hidden, false);
  for (const error of ['NotAllowedError', 'NotFoundError']) {
    const app = voiceApp({ recordingError: error });
    await app.fire('home-tap-target', 'click');
    assert.equal(app.run('currentTab'), 'home');
    assert.equal(app.node('voice-feedback').hidden, false);
    assert.equal(app.context.openedBank, undefined);
  }
  const app = voiceApp();
  await app.fire('home-tap-target', 'click');
  assert.equal(app.run('isListening'), true);
  await app.fire('btn-stop-listening', 'click', { stopPropagation() {} });
  assert.equal(app.run('isListening'), false);
  assert.equal(app.node('voice-transcript').textContent, 'আপনি বলেছেন: “পূবালী ব্যাংক”');
  assert.equal(app.context.openedBank, 102);
  const doubleTap = voiceApp();
  await doubleTap.fire('home-tap-target', 'click', { timeStamp: 1000 });
  assert.equal(doubleTap.run('isListening'), true);
  await doubleTap.fire('home-tap-target', 'click', { timeStamp: 5000 });
  assert.equal(doubleTap.run('isListening'), true, 'single tap while recording keeps listening');
  await doubleTap.fire('home-tap-target', 'click', { timeStamp: 6000 });
  assert.equal(doubleTap.run('isListening'), true, 'separate taps must not stop recording');
  await doubleTap.fire('home-tap-target', 'click', { timeStamp: 6200 });
  assert.equal(doubleTap.run('isListening'), false);
  assert.equal(doubleTap.context.openedBank, 102, 'double tap stops and searches the recorded input');
  for (const code of ['voice_unconfigured', 'voice_unavailable', 'voice_rate_limited', 'no_speech']) {
    const failed = voiceApp();
    failed.context.fetch = async () => response([['error', { code }]]);
    await failed.fire('home-tap-target', 'click'); await failed.run('finishRecording()');
    assert.equal(failed.context.openedBank, undefined);
    assert.equal(failed.node('voice-feedback').hidden, false);
    await failed.fire('voice-retry', 'click'); assert.equal(failed.run('isListening'), true);
  }
  const english = voiceApp();
  english.context.fetch = async () => response([['transcript', { text: 'Is Pubali Bank safe?', language: 'en' }], ['result', { type: 'report_card', institution_id: 102, text: 'Pubali information' }]]);
  await english.fire('home-tap-target', 'click'); await english.run('finishRecording()');
  assert.equal(english.document.documentElement.lang, 'en');
  assert.equal(english.context.openedBank, 102, 'language switch must not abort the stream');

  const typed = voiceApp();
  typed.context.fetch = async (url, request) => { assert.equal(url, '/v1/ask'); assert.equal(request.body.get('text'), 'Pubali'); return response([['transcript', { text: 'Pubali', language: 'en' }], ['result', { type: 'report_card', institution_id: 102, text: 'Pubali information' }]]); };
  await typed.run('submitTextQuestion("Pubali")'); assert.equal(typed.context.openedBank, 102);
  const unknown = voiceApp();
  unknown.context.fetch = async () => response([['transcript', { text: 'unknown bank', language: 'en' }], ['result', { type: 'clarify', text: 'Speak again or type', candidates: [] }]]);
  await unknown.fire('home-tap-target', 'click'); await unknown.run('finishRecording()');
  assert.equal(unknown.context.openedBank, undefined);
  assert.equal(unknown.node('voice-text-form').hidden, false);
  console.log('Spec 02 voice UI passed: permission explanation, compressed upload/context, fragmented UTF-8 SSE, input-based routing, automatic language switch, typing and errors');
})().catch(error => { console.error(error); process.exitCode = 1; });
