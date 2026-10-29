/* Conversation lifetime and tap timing; no persistence or provider credentials. */
(function(root){
  class AgentPanel {
    constructor(adapter,clock=globalThis){this.a=adapter;this.clock=clock;this.generation=0;this.active=false;}
    clear(){for(const key of ['tapTimer','silenceTimer','idleTimer','endTimer'])this.clock.clearTimeout(this[key]);this.tapTimer=null;this.recordingTap=null;}
    idle(){this.clock.clearTimeout(this.idleTimer);this.idleTimer=this.clock.setTimeout(()=>this.reset(),120000);}
    async show(result,guided=false){
      this.clear();this.a.interrupt();this.active=true;this.result=result;this.guided=guided;this.silenceRetries=0;this.captureFailures=0;
      const generation=++this.generation;this.a.render(result);if(!this.active||generation!==this.generation)return;this.phase='speaking';this.idle();
      if(result.audio_pending){this.phase='audio-wait';return;}
      const heard=result.speech_format==='paragraph'?false:await this.a.play(result.speech);
      if(!this.active||generation!==this.generation)return;
      if(result.action?.type==='end'){if(heard)return this.reset();this.phase='waiting';this.endTimer=this.clock.setTimeout(()=>{if(this.active&&generation===this.generation)this.reset()},4000);return;}
      if(['stop','open_report','open_proof'].includes(result.action?.type)){this.phase='waiting';return;}
      this.phase='waiting';
      if(heard&&!this.result.offer_typing){this.phase='starting';await this.a.listen();if(!this.active||generation!==this.generation)return;this.phase=this.a.recording()?'listening':'waiting';}
      if(this.phase==='waiting')this.silent();
    }
    async deliverSpeech(data){
      if(!this.active||this.phase!=='audio-wait')return;
      const generation=this.generation;this.phase='speaking';
      const heard=await this.a.play(data.audio_urls||[data.audio_url]);
      if(!this.active||generation!==this.generation)return;
      if(this.result.action?.type==='end')return this.reset();
      this.phase='waiting';
      if(heard&&!this.result.offer_typing){this.phase='starting';await this.a.listen();if(!this.active||generation!==this.generation)return;this.phase=this.a.recording()?'listening':'waiting';}
      if(this.phase==='waiting')this.silent();
    }
    speechUnavailable(){
      if(!this.active)return;this.clear();++this.generation;this.a.cancel();this.a.interrupt();this.phase='waiting';this.idle();this.silent();
    }
    captureFailed(retryable=false){
      if(!this.active)return;
      this.captureFailures=(this.captureFailures||0)+1;
      if(!retryable||this.captureFailures>=2){this.result.offer_typing=true;this.silenceRetries=2;this.a.typing?.();}
      this.silent();
    }
    async choose(choice){
      if(!this.active)return;
      this.clear();++this.generation;this.phase='searching';this.a.cancel();this.a.interrupt();this.idle();
      return this.a.send(choice);
    }
    tap(event={}){
      if(!this.active||['starting','searching'].includes(this.phase))return;
      this.idle();
      if(this.a.recording()){
        const now=this.clock.now?this.clock.now():Date.now(),delta=now-this.recordingTap;
        if(event.detail===0||(this.recordingTap!=null&&delta>=0&&delta<=450)){this.recordingTap=null;this.phase='searching';this.a.finish();}
        else this.recordingTap=now;
        return;
      }
      const speaking=['speaking','audio-wait'].includes(this.phase);
      this.a.interrupt();++this.generation;this.phase='waiting';
      if(speaking){this.clear();return this.a.listen();}
      if(!this.guided)return this.a.listen();
      if(event.detail===0||this.a.assistive()){this.clock.clearTimeout(this.tapTimer);this.tapTimer=null;return this.choose(this.result.next.options[0]?.value||'listen');}
      if(this.tapTimer!=null){this.clock.clearTimeout(this.tapTimer);this.tapTimer=null;return this.choose(this.result.next.options[1]?.value||'end');}
      this.tapTimer=this.clock.setTimeout(()=>{this.tapTimer=null;this.choose(this.result.next.options[0]?.value||'listen');},450);
    }
    silent(){
      if(!this.active)return;this.phase='waiting';this.clock.clearTimeout(this.silenceTimer);
      if(this.result?.offer_typing)return;
      if(this.silenceRetries>=2)return;
      const generation=this.generation;
      this.silenceTimer=this.clock.setTimeout(async()=>{
        if(!this.active||generation!==this.generation)return;
        this.silenceRetries++;this.phase='speaking';const heard=await this.a.question(this.result.conversation.state);
        if(!this.active||generation!==this.generation)return;
        this.phase='waiting';if(heard){await this.a.listen();if(this.active&&generation===this.generation)this.phase=this.a.recording()?'listening':'waiting';}
      },8000);
    }
    suspend(){this.clear();++this.generation;this.phase='waiting';this.a.cancel();this.a.interrupt();if(this.active)this.idle();}
    reset(){this.active=false;this.clear();++this.generation;this.a.cancel();this.a.interrupt();this.a.exit();}
  }
  root.IlmaAgentPanel=AgentPanel;
  if(typeof module!=='undefined')module.exports={AgentPanel};
})(typeof window!=='undefined'?window:globalThis);
