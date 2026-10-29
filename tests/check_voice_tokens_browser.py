"""Preview browser playback using a model-free bank action and synthetic audio.
No ASR, Spark or TTS provider is called. This is not physical-device acceptance.
"""
import argparse,io,json,math,struct,wave
import httpx
from playwright.sync_api import sync_playwright

p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8018');args=p.parse_args();base=args.base_url.rstrip('/')
audio=io.BytesIO()
with wave.open(audio,'wb') as wav:
    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
    wav.writeframes(b''.join(struct.pack('<h',int(1800*math.sin(2*math.pi*440*i/16000))) for i in range(16000)))
with httpx.Client(timeout=30) as client,sync_playwright() as pw:
    banks=client.get(base+'/v1/institutions?list=demo').json();bank=banks[0]
    browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');errors=[];requests=[];polls=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url) if '/v1/audio/' in r.url else None)
    page.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true,micExplained:true,language:'en',speak:true}));window.mediaEvents=[];window.micAt=[];")
    def ask(route):
        response=client.post(base+'/v1/ask',json={'choice':'bank_1','context':{'agent':True,'speak':False,'ui_lang':'en','conversation':{'institution_id':bank['id'],'compare_bank_ids':[bank['id']],'language':'en'}}})
        response.raise_for_status()
        frames=response.text.split('\n\n');result=next(json.loads(line[6:]) for frame in frames if frame.startswith('event: result') for line in frame.splitlines() if line.startswith('data: '))
        assert not any(step['stage']=='PLAN' for step in result['trace']['steps'])
        result['audio_pending']=True;ticket={'role':'answer','audio_url':'/v1/audio/'+'a'*32+'.mp3'}
        route.fulfill(content_type='text/event-stream',body='event: result\ndata: '+json.dumps(result)+'\n\nevent: speech\ndata: '+json.dumps(ticket)+'\n\nevent: speech\ndata: '+json.dumps(ticket)+'\n\n')
    def status(route):
        polls.append(1);route.fulfill(json={'state':'pending' if len(polls)<3 else 'ready','retry_after':.1})
    page.route('**/v1/ask',ask);page.route('**/v1/audio/*/status',status)
    page.route('**/v1/audio/*.mp3',lambda route:route.fulfill(body=audio.getvalue(),content_type='audio/wav'))
    page.route('**/v1/speech',lambda route:route.abort())
    page.goto(base,wait_until='networkidle')
    page.evaluate('''()=>{
      window.IlmaVoiceRecorder=class {static supported(){return true}async start(){micAt.push(performance.now())}cancel(){}};
      window.IlmaBargeMonitor=class {start(callback){window.testBarge=callback;window.testBargeGeneration=agentPanel.generation}cancel(){}};
      const player=document.getElementById('ilma-player');for(const name of ['playing','ended'])player.addEventListener(name,()=>{if(player.currentSrc.includes('/v1/audio/'))mediaEvents.push({name,at:performance.now()})});
      const button=document.createElement('button');button.id='test-answer';button.textContent='Start playback';button.onclick=()=>{IlmaAudioSession.unlock(player);submitTextQuestion('Synthetic banking question')};document.querySelector('header').appendChild(button);
    }''')
    page.locator('#test-answer').click();page.wait_for_function('()=>micAt.length>0',timeout=20000)
    events=page.evaluate('mediaEvents');ended=[e for e in events if e['name']=='ended'];mp3=[url for url in requests if url.endswith('.mp3')]
    assert len(mp3)==1 and len(ended)==1,(requests,events)
    assert len(polls)==3 and page.evaluate('micAt[0]')-ended[0]['at']>=290
    assert not errors,errors
    summary={'answer_mp3_requests':len(mp3),'status_polls':len(polls),'ended_events':len(ended),'echo_delay_ms':round(page.evaluate('micAt[0]')-ended[0]['at']),'page_errors':errors}
    page.evaluate('agentPanel.suspend()');barge=[]
    for method in ('button','tap','voice'):
        before=len([url for url in requests if url.endswith('.mp3')])
        page.locator('#test-answer').click()
        page.wait_for_function("()=>agentPanel.phase==='speaking'&&!document.getElementById('ilma-player').paused&&testBargeGeneration===agentPanel.generation",timeout=15000)
        value=page.evaluate('''method=>{
          const player=document.getElementById('ilma-player'),started=performance.now();
          if(method==='button')document.getElementById('agent-stop-speech').click();
          else if(method==='tap')document.getElementById('agent-tap').click();
          else testBarge({getTracks:()=>[{stop(){}}]});
          return {method,ms:performance.now()-started,paused:player.paused};
        }''',method)
        assert value['paused'] and value['ms']<300,value
        assert len([url for url in requests if url.endswith('.mp3')])-before==1
        barge.append(value);page.evaluate('agentPanel.suspend()')
    assert not errors,errors
    summary['barge']=barge;print(json.dumps(summary));browser.close()
