"""Opt-in live-provider round trip using a private generated WAV as a fake mic.
Requires Chromium, Meta/TTS configured on target, and an explicit private input.
Does not establish human ASR accuracy, noise tolerance or native accessibility.
"""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8018');p.add_argument('--audio-file',type=Path,required=True);p.add_argument('--bank-slug',required=True);p.add_argument('--language',choices=['bn','en'],default='bn');args=p.parse_args()
audio_file=args.audio_file.resolve(strict=True)
with sync_playwright() as pw:
 browser=pw.chromium.launch(args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-audio-capture='+str(audio_file)])
 try:
  context=browser.new_context(viewport={'width':390,'height':844},permissions=['microphone'],service_workers='block');page=context.new_page();errors=[];uploads=[];urls=set()
  page.on('pageerror',lambda e:errors.append(str(e)))
  def requested(r):
   if '/v1/audio/' in r.url:urls.add(r.url)
   if r.url.endswith('/v1/voice'):uploads.append({'type':r.headers.get('content-type','')})
  page.on('request',requested)
  page.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true,micExplained:true,language:"+json.dumps(args.language)+",speak:true}))")
  page.goto(args.base_url,wait_until='networkidle')
  banks=page.request.get(args.base_url.rstrip('/')+'/v1/institutions?list=demo').json();expected=next(b['id'] for b in banks if b['slug']==args.bank_slug)
  page.evaluate('''()=>{
   window.probeFrames=[];window.probePlayback=[];window.probeCapture=[];const original=handleVoiceEvent;const originalSend=sendVoiceInput;sendVoiceInput=(audio,...rest)=>{if(audio)probeCapture.push({bytes:audio.size,type:audio.type});return originalSend(audio,...rest)};
   handleVoiceEvent=async(name,data,request)=>{if(['transcript','result','error'].includes(name))probeFrames.push({name,ms:Math.round(performance.now()-probeStart),language:data.language,type:data.type,bank:data.conversation?.institution_id,state:data.conversation?.state,code:data.code,asr:data.trace?.steps.find(s=>s.stage==='ASR')});return original(name,data,request)};
   const player=document.getElementById('ilma-player');for(const name of ['playing','ended','error'])player.addEventListener(name,()=>{if(player.currentSrc.includes('/v1/audio/'))probePlayback.push({name,ms:Math.round(performance.now()-probeStart)})});window.probeStart=performance.now();
  }''')
  page.locator('#home-tap-target').click()
  page.wait_for_function("()=>probeFrames.some(f=>f.name==='error')||document.getElementById('voice-feedback').open||(probeFrames.some(f=>f.name==='result')&&probePlayback.some(e=>e.name==='ended')&&isListening)",timeout=90000)
  data=page.evaluate('()=>({frames:probeFrames,playback:probePlayback,capture:probeCapture,listening:isListening})');page.evaluate('agentPanel?.suspend();stopListening()')
  result=next((f for f in data['frames'] if f['name']=='result'),None)
  assert result and result['bank']==expected and result['state']=='BANK' and result['language']==args.language,data
  assert result['asr']['status']=='ok' and result['asr']['model']!='none',data
  assert len(uploads)==1 and len(data['capture'])==1 and data['capture'][0]['bytes']>0 and uploads[0]['type'].startswith('multipart/form-data'),uploads
  assert len(urls)==1 and len([e for e in data['playback'] if e['name']=='ended'])==1 and data['listening'],data
  assert not errors,errors
  print(json.dumps({'frames':data['frames'],'playback':data['playback'],'uploads':len(uploads),'capture':data['capture'],'audio_clips':len(urls)}))
 finally:
  browser.close()
print('Browser capture -> compressed upload -> ffmpeg -> real Meta -> database -> one TTS clip -> mic reopened. Input was generated test speech; native/human acceptance remains separate.')
