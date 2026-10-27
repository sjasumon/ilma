const assert = require('node:assert/strict');
const { createApp } = require('./frontend_harness.cjs');
for (const options of [{}, { reducedMotion: true }, { animationThrows: true }]) {
  const app = createApp(options);
  const frames = ['কথা বলতে যেকোনো জায়গায় ট্যাপ করুন', 'ইস্টার্ন ব্যাংক কেমন আছে?'];
  assert.equal(app.text(), frames[0]);
  assert.equal(app.timerCount(), 1);
  // More than two rounds: text must keep advancing automatically.
  for (let i = 1; i <= 12; i++) { app.tick(); assert.equal(app.text(), frames[i % 2]); }
  app.emit('pointerdown'); app.emit('keydown');
  assert.equal(app.timerCount(), 1, 'ordinary interaction must not permanently cancel rotation');
  app.document.hidden = true; app.emit('visibilitychange');
  assert.equal(app.timerCount(), 0);
  app.document.hidden = false; app.emit('visibilitychange');
  assert.equal(app.timerCount(), 1);
  app.tick(); assert.equal(app.text(), frames[1]);
  app.run('switchTab("services")'); assert.equal(app.timerCount(), 0);
  app.run('switchTab("home")'); assert.equal(app.timerCount(), 1);
  app.tick(); assert.equal(app.text(), frames[1]);
  app.run('isListening = true; pauseGreetingCycle()');
  assert.equal(app.timerCount(), 0);
  app.run('stopListening()'); assert.equal(app.timerCount(), 1);
  app.tick(); assert.equal(app.text(), frames[1]);
  if (options.reducedMotion) assert.equal(app.animationCount(), 0);
}
console.log('Greeting lifecycle passed: startup, 12 automatic transitions, interaction, visibility, tabs, listening, reduced motion, unsupported animation');

const app = createApp();
app.fire('lang-btn', 'click');
assert.equal(app.document.documentElement.lang, 'en');
assert.equal(app.node('lang-btn').textContent, 'BN');
for (let i = 0; i < 8; i++) {
  assert.equal(app.node('home-greeting-line').lang, 'en');
  assert.ok(!/[\u0980-\u09ff]/.test(app.text()));
  app.tick();
}
function gesture(dx, dy = 0, extras = {}) {
  const pointer = { pointerId: 1, isPrimary: true, pointerType: 'touch', clientX: 250, clientY: 100 };
  app.fire('home-tap-target', 'pointerdown', { ...pointer, ...extras });
  app.fire('home-tap-target', 'pointerup', { ...pointer, clientX: 250 + dx, clientY: 100 + dy, ...extras });
}
gesture(-120);
assert.equal(app.document.documentElement.lang, 'bn');
for (let i = 0; i < 8; i++) { assert.equal(app.node('home-greeting-line').lang, 'bn'); app.tick(); }
assert.equal(app.run('suppressHomeClick'), true);
app.fire('home-tap-target', 'click');
assert.equal(app.run('suppressHomeClick'), false);
assert.equal(app.run('currentTab'), 'home', 'swipe must not trigger speech fallback');
for (const [dx, dy] of [[120, 0], [-20, 0], [-80, 150]]) {
  gesture(dx, dy); assert.equal(app.document.documentElement.lang, 'bn');
}
gesture(-120, 0, { pointerType: 'mouse', button: 2 });
assert.equal(app.document.documentElement.lang, 'bn');
gesture(-120, 0, { pointerType: 'mouse', button: 0 });
assert.equal(app.document.documentElement.lang, 'en');
gesture(-120, 0, { pointerType: 'mouse', button: 0 });
assert.equal(app.document.documentElement.lang, 'bn');
app.fire('settings-btn', 'click');
assert.equal(app.node('settings-dialog').open, true);
assert.equal(app.timerCount(), 0);
app.node('settings-language').value = 'en';
app.fire('settings-language', 'change');
assert.equal(app.document.documentElement.lang, 'en');
assert.equal(app.timerCount(), 0, 'settings must keep background rotation paused');
app.node('settings-swipe').checked = false;
app.fire('settings-swipe', 'change');
assert.equal(JSON.parse(app.stored.get('ilma-settings')).swipe, false);
app.fire('settings-close', 'click');
assert.equal(app.node('settings-dialog').open, false);
assert.equal(app.timerCount(), 1);
gesture(-120);
assert.equal(app.document.documentElement.lang, 'en');
app.node('settings-motion').checked = false;
app.fire('settings-motion', 'change');
assert.equal(app.run('greetingMotionReduced()'), true);
assert.equal(JSON.parse(app.stored.get('ilma-settings')).language, 'en');
console.log('Language/settings passed: language-only frames, toggle, left swipe, click suppression, rejected gestures, saved preferences and dialog lifecycle');

const restored = createApp({ savedSettings: { language: 'en', motion: false, swipe: false } });
assert.equal(restored.text(), 'Tap anywhere to speak');
assert.equal(restored.document.documentElement.lang, 'en');
assert.equal(restored.node('lang-btn').textContent, 'BN');
assert.equal(restored.node('settings-swipe').checked, false);
assert.equal(restored.animationCount(), 0);
const blockedStorage = createApp({ storageBlocked: true });
blockedStorage.fire('lang-btn', 'click');
assert.equal(blockedStorage.document.documentElement.lang, 'en');
assert.equal(blockedStorage.timerCount(), 1);
console.log('Preference restore and unavailable storage passed');

const touchApp = createApp({ pointerEvents: false });
const touch = { identifier: 9, clientX: 250, clientY: 120 };
touchApp.fire('home-tap-target', 'touchstart', { touches: [touch] });
touchApp.fire('home-tap-target', 'touchend', { touches: [], changedTouches: [{ ...touch, clientX: 150 }] });
assert.equal(touchApp.document.documentElement.lang, 'en');
touchApp.fire('home-tap-target', 'click');
assert.equal(touchApp.run('currentTab'), 'home');
touchApp.fire('home-tap-target', 'touchstart', { touches: [touch] });
touchApp.fire('home-tap-target', 'touchcancel');
touchApp.fire('home-tap-target', 'touchend', { touches: [], changedTouches: [{ ...touch, clientX: 100 }] });
assert.equal(touchApp.document.documentElement.lang, 'en');
const cancelled = createApp();
cancelled.fire('home-tap-target', 'pointerdown', { pointerId: 1, pointerType: 'touch', clientX: 250, clientY: 100 });
cancelled.fire('home-tap-target', 'pointercancel');
cancelled.fire('home-tap-target', 'pointerup', { pointerId: 1, clientX: 100, clientY: 100 });
assert.equal(cancelled.document.documentElement.lang, 'bn');
console.log('Swipe input paths passed: touch, left mouse drag, right mouse rejection, legacy Touch Events and cancellation');
