/* Unlock one reusable audio context and media element during a user gesture. */
(function(root){
 let context=null,unlocked=false,pending=false;
 function getContext(){if(!context||context.state==='closed'){const C=root.AudioContext||root.webkitAudioContext;context=new C()}return context}
 function unlock(player){
  try{getContext().resume().catch(()=>{})}catch{}
  if(player?.src&&!player.paused){unlocked=true;return;}
  if(unlocked||pending||!player||!root.URL?.createObjectURL)return;
  pending=true;
  // Ten milliseconds of generated silence; no recording or external request.
  const bytes=new Uint8Array(124),view=new DataView(bytes.buffer);
  const word=(offset,text)=>{for(let i=0;i<text.length;i++)bytes[offset+i]=text.charCodeAt(i)};
  word(0,'RIFF');view.setUint32(4,116,true);word(8,'WAVEfmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,8000,true);view.setUint32(28,8000,true);view.setUint16(32,1,true);view.setUint16(34,8,true);word(36,'data');view.setUint32(40,80,true);bytes.fill(128,44);
  const url=root.URL.createObjectURL(new Blob([bytes],{type:'audio/wav'})),volume=player.volume;
  player.volume=0;player.src=url;
  Promise.resolve(player.play()).then(()=>{unlocked=true}).catch(()=>{}).finally(()=>{player.volume=volume;pending=false;setTimeout(()=>root.URL.revokeObjectURL(url),1000)});
 }
 // Safari's call mode can outlast the microphone, so each use names its mode.
 function setMode(type){try{if(root.navigator?.audioSession)root.navigator.audioSession.type=type}catch{}}
 function forPlayback(){setMode('playback');if(context?.state==='running')context.suspend().catch(()=>{})}
 function forRecording(){setMode('play-and-record')}
 root.IlmaAudioSession={getContext,unlock,forPlayback,forRecording};
 root.document?.addEventListener('visibilitychange',()=>{if(root.document.hidden&&context?.state==='running')context.suspend().catch(()=>{})});
})(window);
