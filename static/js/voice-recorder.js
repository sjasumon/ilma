/* Short-lived microphone audio. No storage, browser speech service or API keys. */
(function () {
  class VoiceRecorder {
    static supported() {
      return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder && (window.AudioContext || window.webkitAudioContext));
    }
    constructor() {
      this.cancelled = false;
      this.chunks = [];
      this.finishing = false;
    }
    async start({ onComplete, onError, onLevel = () => {}, onNoise = () => {}, silenceMs = 1500, maxMs = 15000 }) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.context = new AudioContext();
      // Resume during the user's tap, before waiting for the permission prompt.
      const resume = this.context.resume();
      resume.catch(() => {});
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
        if (this.cancelled) { this.cleanup(); return; }
        await resume;
        const types = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm'];
        const mimeType = types.find(type => window.MediaRecorder.isTypeSupported(type));
        this.media = new window.MediaRecorder(this.stream, mimeType ? { mimeType } : undefined);
        this.media.ondataavailable = event => { if (event.data.size && !this.cancelled) this.chunks.push(event.data); };
        this.stopped = new Promise((resolve, reject) => {
          this.resolveStop = resolve;
          this.media.onstop = resolve;
          this.media.onerror = () => { reject(new Error('audio-capture')); onError('audio-capture'); };
        });
        // Prevent an unhandled rejection if recording is cancelled before finish.
        this.stopped.catch(() => {});
        const source = this.context.createMediaStreamSource(this.stream);
        this.analyser = this.context.createAnalyser();
        this.analyser.fftSize = 1024;
        source.connect(this.analyser);
        const mute = this.context.createGain();
        mute.gain.value = 0;
        this.analyser.connect(mute).connect(this.context.destination);
        this.media.start();
        const started = Date.now();
        let lastSpeech = null, noiseTotal = 0, noiseCount = 0, noiseFloor = 0;
        const samples = new Float32Array(this.analyser.fftSize);
        this.monitor = setInterval(() => {
          this.analyser.getFloatTimeDomainData(samples);
          const rms = Math.sqrt(samples.reduce((total, value) => total + value * value, 0) / samples.length);
          const now = Date.now();
          onLevel(rms);
          if (now - started < 300) { noiseTotal += rms; noiseCount++; return; }
          if (!noiseFloor && noiseCount) { noiseFloor = noiseTotal / noiseCount; if (noiseFloor > .035) onNoise(); }
          if (rms > Math.max(.015, Math.min(.03, noiseFloor * 1.8))) lastSpeech = now;
          if (lastSpeech !== null && now - lastSpeech >= silenceMs) this.complete(onComplete);
          else if (lastSpeech === null && now - started >= 6000) { this.cancel(); onError('no-speech'); }
        }, 100);
        this.deadline = setTimeout(() => {
          if (maxMs <= 6000 && lastSpeech === null) { this.cancel(); onError('no-speech'); }
          else this.complete(onComplete);
        }, Math.min(15000, Math.max(1000, maxMs)));
      } catch (error) {
        this.cleanup();
        throw error;
      }
    }
    complete(callback) {
      if (this.cancelled || this.finishing) return;
      this.finishing = true;
      this.clearTimers();
      callback();
    }
    async finish() {
      if (this.cancelled || !this.media) throw new Error('cancelled');
      this.finishing = true;
      this.clearTimers();
      try {
        if (this.media.state !== 'inactive') this.media.stop();
        this.stream?.getTracks().forEach(track => track.stop());
        await Promise.race([this.stopped, new Promise((_, reject) => {
          this.stopWaitTimer = setTimeout(() => reject(new Error('recording_finalize_timeout')), 5000);
        })]);
        if (this.cancelled) throw new Error('cancelled');
        const recording = new Blob(this.chunks, { type: this.media.mimeType });
        this.chunks = [];
        if (this.cancelled) throw new Error('cancelled');
        return recording;
      } finally { this.cleanup(); }
    }
    clearTimers() { clearInterval(this.monitor); clearTimeout(this.deadline); clearTimeout(this.stopWaitTimer); }
    cleanup() {
      this.clearTimers();
      this.stream?.getTracks().forEach(track => track.stop());
      if (this.context && this.context.state !== 'closed') this.context.close().catch(() => {});
      this.chunks = [];
    }
    cancel() {
      this.cancelled = true;
      if (this.media?.state === 'recording') this.media.stop();
      this.resolveStop?.();
      this.cleanup();
    }
  }
  window.IlmaVoiceRecorder = VoiceRecorder;
})();
