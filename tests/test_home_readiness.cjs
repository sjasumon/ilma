const assert = require('node:assert/strict');
const fs = require('node:fs');
const { createApp } = require('./frontend_harness.cjs');
const html = fs.readFileSync('static/index.html', 'utf8');
const target = html.match(/<button id="home-tap-target"[^>]*>/)[0];
assert.match(target, /\sdisabled(?:\s|>)/);
assert.match(target, /aria-busy="true"/);
assert.match(html, /id="home-loading"[^>]*role="status"/);
const app = createApp({autoStart:false, savedSettings:{micExplained:false}});
const button = app.node('home-tap-target');
let disabled = true;
Object.defineProperty(button, 'disabled', {get:()=>disabled, set:value=>{
  if (!value) {
    assert.ok(button.handlers.get('click')?.length, 'install primary click before enabling');
    assert.ok(app.node('mic-permission-allow').handlers.get('click')?.length, 'install microphone consent before enabling');
  }
  disabled=value;
}});
button.setAttribute('aria-busy', 'true');
app.node('home-loading').hidden=false;
app.node('home-idle-view').hidden=true;
app.node('home-listening-view').hidden=true;
assert.equal(button.disabled, true);
assert.equal(button.handlers.get('click'), undefined);
app.emit('DOMContentLoaded');
assert.equal(button.disabled, false);
assert.equal(button.attributes['aria-busy'], 'false');
assert.equal(app.node('home-loading').hidden, true);
assert.equal(app.node('home-idle-view').hidden, false);
app.fire('home-tap-target', 'click');
assert.equal(app.node('mic-permission-dialog').open, true);
assert.equal(app.recorders.length, 0, 'readiness never bypasses microphone consent');
console.log('Home readiness passed: static loading state, handler ordering, enablement and consent');
