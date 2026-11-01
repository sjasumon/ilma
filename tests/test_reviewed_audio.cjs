const assert=require('node:assert/strict');
const {createApp}=require('./frontend_harness.cjs');
for(const language of ['bn','en']){
 const app=createApp({savedSettings:{language,micExplained:false}});let plays=0;app.node('ilma-player').play=()=>{plays++;return Promise.resolve()};
 const url='/static/audio/answers/'+language+'/q001.mp3?v=aaaaaaaaaaaaaaaa';
 assert.equal(app.run(`playVoiceAudio(${JSON.stringify(url)},playbackRequest,true)`),true,'Approved answer URL must be accepted by the real player');
 assert.equal(plays,1);
 assert.equal(app.run("playVoiceAudio('/static/audio/answers/../private.mp3',playbackRequest,true)"),false);
 assert.equal(plays,1);
}
console.log('Reviewed answer audio: BN/EN playback allowlist accepts versioned clips and rejects traversal.');
