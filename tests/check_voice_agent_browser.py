"""Browser integration with synthetic recording/playback, actual read-only tools.
Tap/initial-template requests set speak=false: no transcription, PLAN, SAY,
CHECK or TTS provider is called. This is not device/ASR acceptance.
"""
import argparse,json
from email.parser import BytesParser
from email import policy
import httpx
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8018');args=parser.parse_args();base=args.base_url.rstrip('/')
with httpx.Client(timeout=35) as client, sync_playwright() as p:
    banks=client.get(base+'/v1/institutions?list=demo').json();bank=next(b for b in banks if b['slug']=='bracbank')
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');errors=[];choices=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script('''
      localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true,micExplained:true,language:'en',speak:true}));
      Object.defineProperty(HTMLMediaElement.prototype,'src',{get(){return this._src||''},set(v){this._src=v}});
      Object.defineProperty(HTMLMediaElement.prototype,'paused',{get(){return !this._playing}});
      HTMLMediaElement.prototype.play=function(){this._playing=true;this._end=setTimeout(()=>{this._playing=false;this.dispatchEvent(new Event('ended'))},100);return Promise.resolve()};
      HTMLMediaElement.prototype.pause=function(){this._playing=false;clearTimeout(this._end)};
      HTMLMediaElement.prototype.load=function(){this._src=''};
      window.testRecorders=[];
    ''')
    def handle(route):
        message=BytesParser(policy=policy.default).parsebytes(b'Content-Type: '+route.request.headers['content-type'].encode()+b'\r\n\r\n'+route.request.post_data_buffer)
        fields={part.get_param('name',header='content-disposition'):part.get_payload(decode=True) for part in message.iter_parts()}
        context=json.loads(fields['context']);context['speak']=False
        if 'choice' in fields:
            choice=fields['choice'].decode();choices.append(choice)
        else:
            choice='repeat';context['conversation']={'state':'BANK','institution_id':bank['id'],'last_tool':'bank_summary','turn':0}
        response=client.post(base+'/v1/ask',json={'choice':choice,'context':context},headers={'X-ILMA-Device':route.request.headers.get('x-ilma-device','synthetic-test-device-123456')})
        assert response.status_code==200,(response.status_code,response.text[:150])
        frames=response.text.split('\n\n');result=next(json.loads(line[6:]) for frame in frames if frame.startswith('event: result') for line in frame.splitlines() if line.startswith('data: '))
        assert result['type']=='agent_turn',result.get('type')
        assert all(step['model'] in {'none','script','template','code','database/rules'} for step in result['trace']['steps'])
        result['audio_pending']=True
        route.fulfill(content_type='text/event-stream',body='event: transcript\ndata: '+json.dumps({'text':bank['name_en'],'language':'en'})+'\n\nevent: result\ndata: '+json.dumps(result)+'\n\nevent: speech\ndata: '+json.dumps({'audio_url':'data:audio/mpeg;base64,AA==','audio_urls':['data:audio/mpeg;base64,AA==']})+'\n\n')
    page.route('**/v1/voice',handle);page.route('**/v1/ask',handle)
    page.route('**/v1/speech',lambda route:route.fulfill(json={'audio_url':'data:audio/mpeg;base64,AA==','text':'Synthetic question playback'}))
    page.goto(base,wait_until='networkidle')
    page.evaluate('''()=>{window.IlmaVoiceRecorder=class{static supported(){return true}constructor(){testRecorders.push(this)}async start(callbacks){this.callbacks=callbacks}cancel(){}async finish(){return new Blob(['synthetic'],{type:'audio/webm'})}}}''')
    def begin():
        page.locator('#home-tap-target').click();page.wait_for_function('()=>isListening');page.locator('#home-tap-target').dblclick(delay=100)
        page.wait_for_function("()=>agentConversation?.state==='BANK' && isListening")
    begin();assert page.evaluate("currentTab==='home'")
    for value,state in [('services','SERVICES'),('fdr','SERVICE'),('compare','COMPARE'),('bank','BANK')]:
        page.locator('#agent-options button').filter(has_text={'services':'Bank services','fdr':'FDR','compare':'Compare','bank':'First bank'}[value]).click()
        page.wait_for_function('(state)=>agentConversation?.state===state && isListening',arg=state)
        assert page.evaluate("currentTab==='home'")
        assert page.locator('#agent-trace li').count()==5
        assert page.locator('#agent-options button').count()<=4
    assert choices==['services','fdr','compare','bank']
    assert 'conversation' not in page.evaluate("localStorage.getItem('ilma-settings')")
    page.locator('#agent-card summary').click();page.locator('#agent-sentences .agent-source').first.click();page.locator('#proof-modal.open').wait_for();page.locator('#proof-modal-close').click()
    page.locator('.dock [data-tab="services"]').click();assert page.evaluate('agentConversation===null')
    page.locator('.dock [data-tab="home"]').click();begin()
    page.locator('#agent-report').click();page.wait_for_function("()=>currentTab==='detail' && agentConversation===null")
    assert page.locator('#agent-panel').is_hidden()
    page.locator('.dock [data-tab="home"]').click();begin()
    for width,height in [(320,640),(844,390),(390,300),(1440,900)]:
        page.set_viewport_size({'width':width,'height':height})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        for selector in ['header','.dock']:
            box=page.locator(selector).bounding_box();assert box['y']>=0 and box['y']+box['height']<=height+1
    page.reload(wait_until='networkidle');assert page.evaluate('agentConversation===null') and page.locator('#agent-panel').is_hidden()
    assert not errors,errors
    browser.close()
print('Agent browser passed: model-free sourced tool path, Home-only conversation, five trace rows, source sheet, explicit full report, tab/reload reset and responsive chrome. Media is synthetic.')
