// Exercise actual app startup and scheduled callbacks with a deterministic clock.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function createApp({ reducedMotion = false, animationThrows = false, savedSettings = null, storageBlocked = false, pointerEvents = true, recordingSupported = true, recordingError = null } = {}) {
  const recorders = [];
  class Recorder {
    static supported() { return recordingSupported; }
    constructor() { recorders.push(this); }
    async start(callbacks) { this.callbacks = callbacks; if (recordingError) throw Object.assign(new Error(recordingError), { name: recordingError }); }
    async finish() { return new Blob([new Uint8Array(100)], { type: "audio/webm" }); }
    cancel() { this.cancelled = true; }
  }
  const nodes = new Map(), handlers = new Map(), intervals = new Map(), stored = new Map();
  stored.set("ilma-settings", JSON.stringify({ micExplained: true, ...(savedSettings || {}) }));
  let timerId = 0, animationCount = 0;
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, {
      textContent: '', innerHTML: '', value: '', checked: true, style: {}, dataset: {}, children: [],
      classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
      attributes: {}, handlers: new Map(),
      setAttribute(name, value) { this.attributes[name] = value; },
      removeAttribute(name) { delete this.attributes[name]; },
      pause() {}, play() { return Promise.resolve(); },
      addEventListener(name, callback) { if (!this.handlers.has(name)) this.handlers.set(name, []); this.handlers.get(name).push(callback); },
      showModal() { this.open = true; },
      close() { this.open = false; for (const callback of this.handlers.get('close') || []) callback(); },
      querySelectorAll: () => [],
      replaceChildren() { this.children = []; }, appendChild(child) { this.children.push(child); }, focus() {},
      animate() {
        animationCount++;
        if (animationThrows) throw Error('Unsupported animation');
        return { cancel() {} };
      }
    });
    return nodes.get(id);
  };
  const document = {
    hidden: false, body: {style:{}}, documentElement: {}, getElementById: node, querySelector: node,
    createElement: tag => node(`created-${nodes.size}-${tag}`), querySelectorAll: () => [], addEventListener(name, callback) {
      if (!handlers.has(name)) handlers.set(name, []);
      handlers.get(name).push(callback);
    }
  };
  const context = vm.createContext({
    Blob, FormData, AbortController,
    TextDecoder, Uint8Array,
    fetch: async () => ({ ok: false }),
    document, window: { IlmaVoiceRecorder: Recorder, PointerEvent: pointerEvents ? function () {} : undefined, localStorage: { getItem: key => { if (storageBlocked) throw Error("Blocked"); return stored.get(key); }, setItem: (key, value) => { if (storageBlocked) throw Error("Blocked"); stored.set(key, value); } }, scrollTo() {}, addEventListener() {}, matchMedia: () => ({ matches: reducedMotion, addEventListener() {} }) },
    navigator: {}, console, setTimeout: () => 0, clearTimeout() {},
    setInterval(callback, delay) { const id = ++timerId; intervals.set(id, { callback, delay }); return id; },
    clearInterval(id) { intervals.delete(id); }
  });
  vm.runInContext(fs.readFileSync('static/js/app.js', 'utf8'), context);
  const emit = (name, event = {}) => (handlers.get(name) || []).forEach(callback => callback({ key: 'Tab', ...event }));
  emit('DOMContentLoaded');
  return {
    context, document, node, emit, stored, recorders,
    fire(id, name, event = {}) { let result; for (const callback of node(id).handlers.get(name) || []) result = callback({ target: node(id), preventDefault() {}, ...event }); return result; },
    run: code => vm.runInContext(code, context),
    tick() { for (const { callback, delay } of [...intervals.values()]) { assert.equal(delay, 3800); callback(); } },
    timerCount: () => intervals.size, animationCount: () => animationCount,
    text: () => node('home-greeting-line').textContent
  };
}

module.exports = { createApp };
