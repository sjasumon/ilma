"""Opt-in real-browser ten-turn workflow; synthetic APIs/media only, no live DB or voice provider."""
import argparse,io,json,re,wave
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8029');a=p.parse_args()
if not a.base_url.startswith(('http://127.0.0.1:','http://localhost:')):raise SystemExit('Use an isolated localhost static server')
buffer=io.BytesIO()
with wave.open(buffer,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\0\0'*1200)
media=buffer.getvalue();turns=[];errors=[]
INIT=r'''localStorage.setItem('ilma-settings',JSON.stringify({language:'en',micExplained:true,ivrFinished:true,voiceonly:false,speak:true}));
window.captureStarts=0;window.fakeRecordedAt=0;
const track={readyState:'live',stop(){},getSettings(){return {echoCancellation:true}}};
Object.defineProperty(navigator,'mediaDevices',{value:{async getUserMedia(){return {getTracks:()=>[track],getAudioTracks:()=>[track]}}}});
Object.defineProperty(navigator,'permissions',{value:{async query(){return {state:'granted'}}}});
class Context {constructor(){this.state='running';this.destination={}}resume(){this.state='running';return Promise.resolve()}suspend(){this.state='suspended';return Promise.resolve()}createMediaStreamSource(){return {connect(){},disconnect(){}}}createGain(){return {gain:{value:0},connect(){},disconnect(){}}}createAnalyser(){return {fftSize:1024,connect(x){return x},disconnect(){},getFloatTimeDomainData(samples){samples.fill(performance.now()-window.fakeRecordedAt<450?.06:0)}}}}
window.AudioContext=Context;
class Recorder {static isTypeSupported(){return true}constructor(){this.state='inactive';this.mimeType='audio/webm'}start(){this.state='recording';window.fakeRecordedAt=performance.now();window.captureStarts++}stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['synthetic audio'],{type:this.mimeType})});queueMicrotask(()=>this.onstop?.())}}
window.MediaRecorder=Recorder;'''
with sync_playwright() as pw:
 browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');page.add_init_script(INIT);page.on('pageerror',lambda error:errors.append(str(error)))
 def api(route):
  request=route.request
  if request.method=='POST' and request.url.endswith('/v1/voice'):
   raw=request.post_data_buffer or b'';match=re.search(rb'name="context"\r\n\r\n([^\r]+)',raw);assert match,'Missing multipart context';context=json.loads(match[1]);n=len(turns)+1;previous=context.get('conversation',{}).get('conversation_token')
   assert previous==(None if n==1 else 'synthetic-'+str(n-1)),(n,previous)
   turns.append(context);result=dict(type='agent_turn',intent='bank_overview',language='en',speech='Synthetic response.',speech_format='paragraph',audio_pending=True,expects_reply=n%2==0,conversation=dict(state='BANK',turn=n,conversation_token='synthetic-'+str(n),institution_id=1,misses=0),next=dict(question='',options=[]),facts=[],sentences=[],trace=dict(steps=[],status_rule_notice='Synthetic fixture'),action={'type':'end'} if n==10 else None)
   wire='event: result\ndata: '+json.dumps(result)+'\n\nevent: speech\ndata: '+json.dumps(dict(audio_url='/static/audio/answers/en/q001.mp3?v=aaaaaaaaaaaaaaaa'))+'\n\n'
   route.fulfill(status=200,content_type='text/event-stream',body=wire);return
  assert request.method=='GET','Unexpected write endpoint: '+request.url
  body=[] if '/institutions/index' in request.url else {'available':False,'clips':{}} if '/content/fixed' in request.url else {}
  route.fulfill(status=200,content_type='application/json',body=json.dumps(body))
 page.route('**/v1/**',api);page.route('**/static/audio/**',lambda route:route.fulfill(status=200,content_type='audio/wav',body=media))
 page.goto(a.base_url,wait_until='networkidle');page.click('#home-tap-target');page.wait_for_function('window.captureStarts>=10',timeout=60000)
 page.wait_for_function("document.querySelector('#agent-panel').hidden",timeout=15000)
 assert len(turns)==10 and page.evaluate('window.captureStarts')==10
 assert not page.evaluate('isListening') and not errors,errors
 browser.close()
print('Real browser passed10 voice turns after one initial tap: synthetic capture/upload/SSE, real audio-ended events, auto-listen, latest tokens and Finish cleanup. No live APIs used.')
