/* Guided two-choice flow. Timing and cancellation are independent of the DOM. */
(function (root) {
  const IVR_STEPS = {
    open: { id: 'open', clip: 'ivr_open', onTap1: 'mic', onTap2: 'mic', words: {}, onSilence: 'repeat' },
    mic: { id: 'mic', clip: 'ivr_mic', onTap1: 'permission', onTap2: 'permission', words: {}, onSilence: 'repeat' },
    language: { id: 'language', clip: 'ivr_lang', onTap1: 'bn', onTap2: 'en', words: { bn: 'bn', en: 'en' }, onSilence: 'repeat' },
    menu: { id: 'menu', clip: 'ivr_menu', onTap1: 'bank', onTap2: 'services', words: {}, onSilence: 'repeat' },
    name: { id: 'name', clip: 'ivr_name', onTap1: 'listen', onTap2: 'listen', words: {}, onSilence: 'repeat' },
    confirm: { id: 'confirm', clip: 'ivr_confirm', onTap1: 'yes', onTap2: 'no', words: {}, onSilence: 'repeat' },
    report: { id: 'report', clip: null, onTap1: 'next', onTap2: 'next', words: {}, onSilence: null },
    next: { id: 'next', clip: 'ivr_next', onTap1: 'report', onTap2: 'name', words: {}, onSilence: 'repeat' }
  };
  root.IVR_COPY = {"ivr_open": ["আমি ইলমা। শুরু করতে স্ক্রিনের যেকোনো জায়গায় চাপুন।", "I am Ilma. Tap anywhere to start."], "ivr_mic": ["এখন ফোন মাইক্রোফোনের অনুমতি চাইবে। অনুমতি দিন চাপুন।", "Your phone will ask for microphone permission. Choose Allow."], "ivr_lang": ["বাংলার জন্য একবার চাপুন। For English, tap twice. অথবা বলুন।", "Tap once for Bangla. Tap twice for English. Or say your choice."], "ivr_menu": ["ব্যাংকের অবস্থা জানতে একবার চাপুন। ব্যাংকের সেবা জানতে দুবার চাপুন। অথবা সরাসরি ব্যাংকের নাম বলুন।", "Tap once to check a bank. Tap twice for bank services. Or say a bank name."], "ivr_name": ["ব্যাংকের নাম বলুন।", "Say the bank name."], "ivr_confirm": ["আপনি কি {bank} বললেন? হ্যাঁ হলে একবার, না হলে দুবার চাপুন।", "Did you say {bank}? Tap once for yes, twice for no."], "ivr_next": ["আবার শুনতে একবার, অন্য ব্যাংকের জন্য দুবার চাপুন।", "Tap once to hear it again, twice for another bank."], "ivr_chose_bn": ["আপনি বাংলা বেছেছেন।", "You chose Bangla."], "ivr_chose_en": ["আপনি ইংরেজি বেছেছেন।", "You chose English."], "ivr_chose_bank": ["আপনি ব্যাংকের অবস্থা বেছেছেন।", "You chose bank status."], "ivr_chose_services": ["আপনি ব্যাংকের সেবা বেছেছেন।", "You chose bank services."], "ivr_yes": ["হ্যাঁ।", "Yes."], "ivr_no": ["না।", "No."], "ivr_ready": ["বলুন।", "Speak now."], "ivr_repeat_hint": ["আবার শুনতে আবার বলুন।", "Say again to hear it again."]};
  class GuidedVoice {
    constructor(adapter, clock = globalThis) {
      this.a = adapter; this.clock = clock; this.active = false; this.epoch = 0;
    }
    clear() {
      this.clock.clearTimeout(this.tapTimer); this.clock.clearTimeout(this.silenceTimer);
      this.tapTimer = null; this.recordingTap = null;
    }
    async enter(id, repeated = false) {
      if (!IVR_STEPS[id]) return;
      this.clear(); this.a.cancel(); this.active = true; this.id = id;
      this.silenceRetries = repeated ? (this.silenceRetries || 0) + 1 : 0; const epoch = ++this.epoch;
      this.phase = 'speaking'; this.a.render(id); this.a.announce(id);
      const heard = await this.a.prompt(id);
      if (!this.active || epoch !== this.epoch) return;
      this.phase = 'waiting';
      if (id === 'report') return this.enter('next');
      if (id === 'mic' && heard) return this.a.action('permission');
      // Browsers require a user gesture for playback/permission. Keep choices
      // operable if autoplay is blocked, rather than recording over an unheard clip.
      if (heard && !['open', 'mic'].includes(id)) {
        this.phase = 'starting';
        await this.a.listen(id);
        if (!this.active || epoch !== this.epoch) return;
        if (this.a.recording()) this.phase = 'listening';
      }
      if (this.phase === 'waiting') this.wait();
    }
    wait() {
      this.clock.clearTimeout(this.silenceTimer); this.phase = 'waiting';
      if (this.silenceRetries >= 2 || !IVR_STEPS[this.id].onSilence) return;
      const epoch = this.epoch;
      this.silenceTimer = this.clock.setTimeout(() => {
        if (this.active && epoch === this.epoch) this.enter(this.id, true);
      }, 8000);
    }
    silent() { if (this.active) this.wait(); }
    tap(event = {}) {
      if (!this.active) return;
      if (this.phase === 'searching' || this.phase === 'starting' || this.phase === 'transition') return;
      if (this.a.recording()) {
        // While the mic is open the pair only stops recording, never chooses 2.
        const now = this.clock.now ? this.clock.now() : Date.now();
        if (event.detail === 0 || (this.recordingTap != null && now - this.recordingTap >= 0 && now - this.recordingTap <= 450)) {
          this.recordingTap = null; this.phase = 'searching'; this.a.finish();
        } else this.recordingTap = now;
        return;
      }
      const wasReport = this.id === 'report';
      this.a.interrupt(); ++this.epoch; this.clock.clearTimeout(this.silenceTimer);
      this.phase = 'waiting';
      if (wasReport) return this.enter('next');
      // Native/assistive activation is already a single resolved choice.
      if (event.detail === 0 || this.a.assistive()) {
        this.clock.clearTimeout(this.tapTimer); this.tapTimer = null; return this.choose(1);
      }
      if (this.tapTimer != null) {
        this.clock.clearTimeout(this.tapTimer); this.tapTimer = null; return this.choose(2);
      }
      this.tapTimer = this.clock.setTimeout(() => { this.tapTimer = null; this.choose(1); }, 450);
    }
    async choose(n) {
      if (!this.active) return;
      this.clear(); this.a.cancel(); ++this.epoch; this.phase = 'transition';
      const epoch = this.epoch; await this.a.echo(n, this.id);
      if (!this.active || epoch !== this.epoch) return;
      return this.a.action(IVR_STEPS[this.id][n === 2 ? 'onTap2' : 'onTap1']);
    }
    command(action) {
      if (!this.active) return;
      if (action === 'one' || action === 'two') return this.choose(action === 'one' ? 1 : 2);
      if (IVR_STEPS[this.id].words[action]) return this.choose(action === 'bn' ? 1 : 2);
      if (action === 'again') return this.enter(this.id);
      if (action === 'name') return this.enter('name');
      if (action === 'stop') { this.clear(); ++this.epoch; this.a.cancel(); this.a.interrupt(); this.silenceRetries = 2; return this.wait(); }
      return this.a.read(action);
    }
    skip() {
      this.active = false; ++this.epoch; this.clear(); this.a.cancel(); this.a.interrupt(); this.a.exit();
    }
  }
  root.IlmaGuidedVoice = GuidedVoice; root.IVR_STEPS = IVR_STEPS;
  if (typeof module !== 'undefined') module.exports = { GuidedVoice, IVR_STEPS };
})(typeof window !== 'undefined' ? window : globalThis);
