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
(async()=>{
 const {AgentPanel}=require('../static/js/voice-agent.js');
 const app=createApp({autoStart:false,savedSettings:{micExplained:true}});
 app.context.window.IlmaAgentPanel=AgentPanel;
 app.run('setupAgentPanel()');
 let plays=0;app.node('ilma-player').play=()=>{plays++;return Promise.resolve()};
 const settle=async()=>{for(let i=0;i<20;i++)await Promise.resolve()};
 for(let turn=1;turn<=10;turn++){
  const token='synthetic-token-'+turn;
  const result={type:'agent_turn',intent:'bank_overview',language:'en',speech:'Synthetic answer',speech_format:'paragraph',audio_pending:true,expects_reply:turn%2===0,conversation:{state:'BANK',turn,conversation_token:token,institution_id:1},next:{options:[]},facts:[],sentences:[],trace:{steps:[],status_rule_notice:''}};
  await app.run(`handleVoiceEvent('result',${JSON.stringify(result)},playbackRequest)`);
  await app.run(`handleVoiceEvent('speech',{audio_url:'/static/audio/answers/en/q001.mp3?v=aaaaaaaaaaaaaaaa'},playbackRequest)`);
  await settle();assert.equal(plays,turn,'Conversation player must play saved answer URL');
  assert.equal(app.run('isListening'),false,'Never record over the answer');
  app.fire('ilma-player','ended');await settle();
  assert.equal(app.run('isListening'),true,'Actual app adapter automatically records after every answer');
  assert.equal(app.node('agent-question').textContent,'Listening — speak now','Active microphone must have an explicit speak-now cue');
  assert.equal(app.run('agentConversation.conversation_token'),token,'Latest conversation token survives playback and microphone restart');
  app.run('stopListening()');
 }
 const rejected=await app.run("playGuidedSpeech('agent',null,null,'/static/audio/answers/../private.mp3')");assert.equal(rejected,false);
 assert.equal(plays,10,'Invalid URLs must not reach the player');
 app.run('agentPanel.reset()');
 console.log('Real conversation adapter passed ten saved-answer turns: playback, automatic mic, current tokens and URL rejection.');
})().catch(error=>{console.error(error);process.exitCode=1});
