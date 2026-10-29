"""Opt-in real playback interruption with synthetic microphone handoff.
No human speech, microphone capture or provider-accuracy claim.
"""
import argparse,json
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8018');args=p.parse_args()
with sync_playwright() as pw:
 browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true,micExplained:true,language:'bn',speak:true}))")
 page.goto(args.base_url,wait_until='networkidle')
 page.evaluate('''()=>{
 window.testCaptures=[];
 window.IlmaVoiceRecorder=class {static supported(){return true}async start(options){testCaptures.push(Boolean(options.stream))}cancel(){}};
 window.IlmaBargeMonitor=class {start(callback){window.testBarge=callback}cancel(){}};
 const button=document.createElement('button');button.id='test-start';button.textContent='Start fixed speech';button.onclick=()=>{IlmaAudioSession.unlock(document.getElementById('ilma-player'));submitTextQuestion('প্রাইম ব্যাংক')};document.querySelector('header').appendChild(button);
 }''')
 timings=[]
 for method in ['button','tap','voice']:
  page.locator('#test-start').click()
  page.wait_for_function("()=>!document.getElementById('ilma-player').paused&&agentPanel.phase==='speaking'",timeout=70000)
  page.locator('#agent-stop-speech').wait_for(state='visible')
  result=page.evaluate('''method=>{
    const player=document.getElementById('ilma-player'),started=performance.now();
    if(method==='button')document.getElementById('agent-stop-speech').click();
    else if(method==='tap')document.getElementById('agent-tap').click();
    else testBarge({getTracks:()=>[{stop(){}}]});
    return {method,ms:performance.now()-started,paused:player.paused,stop_hidden:document.getElementById('agent-stop-speech').hidden};
  }''',method)
  assert result['paused'] and result['stop_hidden'] and result['ms']<300,result
  if method!='button':page.wait_for_function('()=>isListening')
  if method=='voice':assert page.evaluate('testCaptures.at(-1)')
  page.evaluate('agentPanel.suspend();stopListening()');timings.append(result)
 assert not errors,errors
 print(json.dumps(timings));browser.close()
print('Real playback interruption passed under 300 ms for Stop, reply tap and synthetic voice-detection handoff. Physical echo rejection and listener comprehension remain separate.')
