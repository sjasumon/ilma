/* Microphone audio for one visit; recordings are short-lived. No storage, browser speech service or API keys. */
(function () {
  let fallbackContext=null;
  // One microphone grant per visit: reuse the live stream, release it when the page is hidden.
  let sessionStream=null;
  async function sessionMicrophone(){
    if(sessionStream?.getAudioTracks().some(track=>track.readyState!=='ended'))return sessionStream;
    if(micClosesForPlayback())window.IlmaAudioSession?.forRecording?.();
    sessionStream=await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    return sessionStream;
  }
  function releaseMicrophone(){sessionStream?.getTracks().forEach(track=>track.stop());sessionStream=null}
  function stopUnlessSession(stream){if(stream&&stream!==sessionStream)stream.getTracks().forEach(track=>track.stop())}
  if(typeof document!=='undefined')document.addEventListener?.('visibilitychange',()=>{if(document.hidden)releaseMicrophone()});
  function sharedContext(){if(window.IlmaAudioSession)return window.IlmaAudioSession.getContext();if(!fallbackContext||fallbackContext.state==='closed'){const C=window.AudioContext||window.webkitAudioContext;fallbackContext=new C()}return fallbackContext}
  class VoiceRecorder {
    static supported() {
      return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder && (window.AudioContext || window.webkitAudioContext));
    }
    constructor() {
      this.cancelled = false;
      this.chunks = [];
      this.finishing = false;
    }
    async start({ stream: providedStream, onComplete, onError, onLevel = () => {}, onNoise = () => {}, silenceMs = 1500, maxMs = 15000, noSpeechMs = 6000 }) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.context = sharedContext();
      // Resume during the user's tap, before waiting for the permission prompt.
      const resume = this.context.resume();
      resume.catch(() => {});
      try {
        this.stream = providedStream || await sessionMicrophone();
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
        const source = this.source = this.context.createMediaStreamSource(this.stream);
        this.analyser = this.context.createAnalyser();
        this.analyser.fftSize = 1024;
        source.connect(this.analyser);
        const mute = this.mute = this.context.createGain();
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
          // A one-word reply may finish during calibration. Never discard it.
          if (now - started < 300) {
            noiseTotal+=rms;noiseCount++;
            if(rms>.015)lastSpeech=now;
          }
          if (now-started>=300 && !noiseFloor && noiseCount) { noiseFloor = noiseTotal / noiseCount; if (noiseFloor > .035) onNoise(); }
          if (rms > Math.max(.015, Math.min(.03, noiseFloor * 1.8))) lastSpeech = now;
          if (lastSpeech !== null && now - lastSpeech >= silenceMs) this.complete(onComplete);
          else if (lastSpeech === null && now - started >= noSpeechMs) { this.cancel(); onError('no-speech'); }
        }, 100);
        this.deadline = setTimeout(() => {
          if (lastSpeech === null) { this.cancel(); onError('no-speech'); }
          else { this.truncated=true; this.complete(onComplete); }
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
        stopUnlessSession(this.stream);
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
      stopUnlessSession(this.stream);
      this.source?.disconnect?.();this.analyser?.disconnect?.();this.mute?.disconnect?.();
      this.chunks = [];
    }
    cancel() {
      this.cancelled = true;
      if (this.media?.state === 'recording') this.media.stop();
      this.resolveStop?.();
      this.cleanup();
    }
  }
  // Only observe with permission already granted; never prompt during playback.
  // Raw levels stay in memory. Echo cancellation support is required.
  class BargeMonitor {
    async start(onSpeech) {
      this.cancelled=false;
      try {
        if(!navigator.permissions?.query)return;
        const permission=await navigator.permissions.query({name:'microphone'});
        if(permission.state!=='granted'||this.cancelled)return;
        this.stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true}});
        if(this.cancelled||this.stream.getAudioTracks()[0]?.getSettings?.().echoCancellation!==true){this.cancel();return;}
        const context=sharedContext();await context.resume();if(this.cancelled)return;
        this.source=context.createMediaStreamSource(this.stream);this.analyser=context.createAnalyser();this.analyser.fftSize=1024;this.source.connect(this.analyser);
        this.mute=context.createGain();this.mute.gain.value=0;this.analyser.connect(this.mute).connect(context.destination);
        const data=new Float32Array(1024);let count=0,floor=0,voiced=0;
        this.monitor=setInterval(()=>{
          this.analyser.getFloatTimeDomainData(data);const rms=Math.sqrt(data.reduce((a,b)=>a+b*b,0)/data.length);
          if(count++<2){floor+=Math.min(rms,.015)/2;return;}
          voiced=rms>Math.max(.035,Math.min(.06,floor*3))?voiced+1:0;
          if(voiced>=4){const stream=this.stream;this.stream=null;this.cancel();onSpeech(stream);}
        },50);
      }catch{this.cancel();}
    }
    cancel(){this.cancelled=true;clearInterval(this.monitor);this.stream?.getTracks().forEach(t=>t.stop());this.stream=null;this.source?.disconnect?.();this.analyser?.disconnect?.();this.mute?.disconnect?.();}
  }
  window.IlmaBargeMonitor=BargeMonitor;
  window.IlmaVoiceRecorder = VoiceRecorder;
  // iOS moves an open microphone's page into its call audio mode, which rides the
  // speech volume up and down. There the mic closes while an answer plays.
  function micClosesForPlayback(){
    const agent=navigator.userAgent||'';
    return /iP(?:hone|ad|od)/.test(agent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  }
  window.IlmaMicrophone={release:releaseMicrophone,closesForPlayback:micClosesForPlayback};
})();
