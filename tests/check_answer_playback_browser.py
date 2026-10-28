"""Opt-in actual TTS playback check with a synthetic recorder, no microphone input.
Use a local preview with Meta/ASR disabled and TTS configured. May generate TTS
on a source-cache miss. Never publish the audio cache or private environment.
"""
import argparse,json
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8018');args=p.parse_args()
with sync_playwright() as pw:
 browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');errors=[];audio_urls=set();cache=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 def response(r):
  if '/v1/audio/' in r.url:audio_urls.add(r.url);cache.append(r.headers.get('x-ilma-cache'))
 page.on('response',response)
 page.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true,micExplained:true,language:'bn',speak:true}));window.playbackMetrics=[];window.syntheticMic=[];")
 page.goto(args.base_url,wait_until='networkidle')
 page.evaluate('''()=>{
  window.IlmaVoiceRecorder=class {static supported(){return true}async start(){syntheticMic.push(performance.now())}cancel(){}};
  const player=document.getElementById('ilma-player');for(const name of ['playing','ended','error'])player.addEventListener(name,()=>{if(player.currentSrc.includes('/v1/audio/'))playbackMetrics.push({name,time:performance.now()})});
  new MutationObserver(()=>{if(!window.answerAt&&document.getElementById('agent-answer').textContent)window.answerAt=performance.now()}).observe(document.getElementById('agent-answer'),{childList:true});
  const button=document.createElement('button');button.id='start-playback-check';button.textContent='Start fixed bank check';button.onclick=()=>{window.startedAt=performance.now();IlmaAudioSession.unlock(player);submitTextQuestion('প্রাইম ব্যাংক')};document.querySelector('header').appendChild(button);
 }''')
 page.locator('#start-playback-check').click();page.wait_for_function('()=>syntheticMic.length>0',timeout=70000)
 data=page.evaluate('''()=>({text_ms:Math.round(answerAt-startedAt),events:playbackMetrics.map(e=>({name:e.name,ms:Math.round(e.time-startedAt)})),mic_ms:Math.round(syntheticMic[0]-startedAt),main_scroll:document.querySelector('main').scrollTop})''')
 ended=[e for e in data['events'] if e['name']=='ended'];assert len(ended)==1 and len(audio_urls)==1,data
 assert data['mic_ms']>=ended[0]['ms'] and data['main_scroll']==0,data
 assert page.locator('#agent-answer').inner_text()==page.evaluate('agentPanel.result.speech')
 assert not page.locator('#agent-card').evaluate('(el)=>el.open')
 page.evaluate('stopListening()');page.locator('#agent-card summary').click()
 texts=page.evaluate('agentPanel.result.sentences.map(s=>s.text)')
 assert all(text in page.locator('#agent-sentences').inner_text() for text in texts)
 assert not errors,errors
 data['unique_audio_urls']=len(audio_urls);data['cache']=cache
 print(json.dumps(data));browser.close()
print('Single-clip playback passed: paragraph first, one actual MP3, no microphone until playback ends, unchanged figures behind an expandable card. Native-device acceptance is separate.')
