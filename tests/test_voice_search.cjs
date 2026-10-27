const assert = require('node:assert/strict');
const { createApp } = require('./frontend_harness.cjs');
function response(events, lineEnding = '\n', failAtEnd = false) {
  // Split across UTF-8 code points and SSE frame boundaries to exercise buffering.
  const bytes = new TextEncoder().encode(events.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`).join('').replace(/\n/g, lineEnding));
  let offset = 0;
  return { ok: true, body: { getReader: () => ({
    async read() { if (offset >= bytes.length) { if (failAtEnd) throw Error('connection lost'); return { done: true }; } const value = bytes.slice(offset, offset + 7); offset += 7; return { value, done: false }; },
    async cancel() {}
  }) } };
}
function voiceApp(options = {}) {
  const app = createApp(options);
  app.context.fetch = async (url, request) => {
    assert.equal(app.node('home-orb').attributes['data-state'], 'thinking');
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
  assert.equal(app.node('home-orb').attributes['data-state'], 'listening');
  assert.equal(app.node('home-tap-target').attributes['aria-pressed'], 'true');
  await app.fire('btn-stop-listening', 'click', { stopPropagation() {} });
  assert.equal(app.run('isListening'), false);
  assert.equal(app.node('voice-transcript').textContent, 'আপনি বলেছেন: “পূবালী ব্যাংক”');
  assert.equal(app.context.openedBank, 102);
  assert.equal(app.node('home-orb').attributes['data-state'], 'idle');
  assert.equal(app.node('home-tap-target').attributes['aria-pressed'], 'false');
  await app.fire('ilma-player', 'playing');
  assert.equal(app.node('home-orb').attributes['data-state'], 'speaking');
  await app.fire('ilma-player', 'error');
  assert.equal(app.node('home-orb').attributes['data-state'], 'idle');
  const reduced = voiceApp({ reducedMotion: true });
  assert.equal(reduced.node('home-orb').attributes['data-reduced-motion'], 'true');
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
  const keyboard = voiceApp();
  await keyboard.fire('home-tap-target', 'click', {detail:0});
  assert.equal(keyboard.run('isListening'), true);
  await keyboard.fire('home-tap-target', 'click', {detail:0});
  assert.equal(keyboard.run('isListening'), false);
  assert.equal(keyboard.context.openedBank, 102, 'assistive/keyboard activation stops with one native activation');
  for (const code of ['voice_unconfigured', 'voice_unavailable', 'voice_rate_limited', 'no_speech']) {
    const failed = voiceApp();
    failed.context.fetch = async () => response([['error', { code }]]);
    await failed.fire('home-tap-target', 'click'); await failed.run('finishRecording()');
    assert.equal(failed.context.openedBank, undefined);
    assert.equal(failed.node('voice-feedback').hidden, false);
    assert.equal(failed.node('voice-feedback').open, true, 'errors open the search dialog');
    await failed.fire('voice-retry', 'click'); assert.equal(failed.run('isListening'), true);
    assert.equal(failed.node('voice-feedback').open, false, 'retry closes the dialog before recording');
  }
  const english = voiceApp();
  const lateDisconnect = voiceApp();
  lateDisconnect.context.fetch = async () => response([
    ['transcript', {text:'Pubali Bank', language:'en'}],
    ['result', {type:'report_card', institution_id:102, text:'Pubali information'}]
  ], '\n', true);
  await lateDisconnect.fire('home-tap-target', 'click');
  await lateDisconnect.run('finishRecording()');
  assert.equal(lateDisconnect.context.openedBank, 102);
  assert.equal(lateDisconnect.run('isSearching'), false);
  assert.match(lateDisconnect.node('sr-announcer').textContent, /answer is shown/);
  const crlf = voiceApp();
  crlf.context.fetch = async () => response([
    ['transcript', {text:'Pubali Bank', language:'en'}],
    ['result', {type:'report_card', institution_id:102, text:'Pubali information'}]
  ], '\r\n');
  await crlf.fire('home-tap-target', 'click');
  await crlf.run('finishRecording()');
  assert.equal(crlf.context.openedBank, 102, 'CRLF split across network chunks must parse');
  const interrupted = voiceApp();
  interrupted.run('currentLang = "en"');
  interrupted.context.fetch = async () => response([['transcript', {text:'Pubali Bank', language:'en'}]]);
  await interrupted.fire('home-tap-target', 'click');
  await interrupted.run('finishRecording()');
  assert.match(interrupted.node('voice-feedback-message').textContent, /connection ended before the answer/);
  assert.match(interrupted.node('voice-transcript').textContent, /Pubali Bank/);
  assert.equal(interrupted.run('isSearching'), false);
  const mismatch = voiceApp();
  mismatch.run('currentLang = "en"');
  mismatch.context.fetch = async () => response([
    ['transcript', {text: 'नमस्ते बैंक', language: 'en', unusable: true}],
    ['error', {code: 'transcript_language_mismatch'}]
  ]);
  await mismatch.fire('home-tap-target', 'click');
  await mismatch.run('finishRecording()');
  assert.match(mismatch.node('voice-transcript').textContent, /नमस्ते बैंक/);
  assert.match(mismatch.node('voice-feedback-message').textContent, /unexpected script/);
  assert.equal(mismatch.node('voice-text-input').value, 'नमस्ते बैंक');
  assert.ok(!mismatch.node('voice-feedback-message').textContent.includes('noisy'));
  const dataFailure = voiceApp();
  dataFailure.context.fetch = async () => response([
    ['transcript', { text: 'Is Pubali Bank safe?', language: 'en' }],
    ['error', { code: 'bank_data_unavailable' }]
  ]);
  await dataFailure.fire('home-tap-target', 'click');
  await dataFailure.run('finishRecording()');
  assert.equal(dataFailure.node('voice-transcript').hidden, false);
  assert.match(dataFailure.node('voice-transcript').textContent, /You said:.*Is Pubali Bank safe/);
  dataFailure.context.fetch = async () => ({ ok: false, status: 503, json: async () => ({ error: {code: 'bank_data_unavailable'} }) });
  await dataFailure.fire('voice-retry', 'click');
  await dataFailure.run('finishRecording()');
  assert.equal(dataFailure.node('voice-transcript').textContent, 'No transcript was received for this attempt.');
  const outdated = voiceApp();
  outdated.run('currentLang = "en"');
  outdated.context.fetch = async () => ({ ok: false, status: 404 });
  await outdated.fire('home-tap-target', 'click');
  await outdated.run('finishRecording()');
  assert.match(outdated.node('voice-feedback-message').textContent, /backend needs to be updated or restarted/);
  assert.equal(outdated.context.openedBank, undefined);
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
  assert.equal(unknown.node('voice-feedback').open, true);
  await unknown.fire('voice-dialog-close', 'click');
  assert.equal(unknown.node('voice-feedback').hidden, true);
  console.log('Spec 02 voice UI passed: permission explanation, compressed upload/context, fragmented UTF-8 SSE, input-based routing, automatic language switch, typing and errors');
})().catch(error => { console.error(error); process.exitCode = 1; });
