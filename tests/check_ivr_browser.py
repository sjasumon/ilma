"""Opt-in guided-flow browser check. Provider/audio/recorder responses are synthetic.
This verifies DOM integration, not real speech recognition or native accessibility.
"""
import argparse,json
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8018');args=parser.parse_args()
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':390,'height':844},service_workers='block')
    errors=[];readouts=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    def speech(route):
        readouts.append(route.request.post_data_json)
        route.fulfill(json={'audio_url':'data:audio/mpeg;base64,AA==','text':'Synthetic prompt'})
    page.route('**/v1/speech',speech)
    page.add_init_script('''
      if (!sessionStorage.getItem('synthetic-init')) { localStorage.clear(); sessionStorage.setItem('synthetic-init','1'); }
      Object.defineProperty(HTMLMediaElement.prototype,'src',{get(){return this._src||''},set(v){this._src=v}});
      Object.defineProperty(HTMLMediaElement.prototype,'paused',{get(){return !this._playing}});
      HTMLMediaElement.prototype.play=function(){this._playing=true;this._end=setTimeout(()=>{this._playing=false;this.dispatchEvent(new Event('ended'))},100);return Promise.resolve()};
      HTMLMediaElement.prototype.pause=function(){this._playing=false;clearTimeout(this._end)};
      HTMLMediaElement.prototype.load=function(){this._src=''};
      window.testRecorders=[];
    ''')
    page.goto(args.base_url,wait_until='networkidle')
    assert page.locator('#ivr-overlay').is_hidden(), 'fresh visit must use normal Home'
    assert not readouts, 'fresh visit must not request guided audio'
    page.locator('#settings-btn').click();page.locator('#settings-voiceonly').check();page.locator('#settings-close').click()
    page.evaluate('''()=>{window.IlmaVoiceRecorder=class {
      static supported(){return true} constructor(){window.testRecorders.push(this)}
      async start(callbacks){this.callbacks=callbacks} cancel(){}
      async finish(){return new Blob(['synthetic audio'],{type:'audio/webm'})}
    }}''')
    page.wait_for_function("() => ivr?.id==='open' && ivr.phase==='waiting'")
    assert page.locator('#ivr-overlay').is_visible()
    page.locator('#ivr-tap').click()
    page.locator('#mic-permission-dialog').wait_for(state='visible')
    page.locator('#mic-permission-allow').click()
    page.wait_for_function("() => ivr.id==='language' && isListening")
    def quiet():
        page.evaluate("window.testRecorders.at(-1).callbacks.onError('no-speech')")
        page.wait_for_function("() => ivr.phase==='waiting' && !isListening")
    quiet();page.locator('#ivr-tap').dblclick(delay=150)
    page.wait_for_function("() => currentLang==='en' && ivr.id==='menu' && isListening")
    quiet();page.locator('#ivr-tap').click()
    page.wait_for_function("() => ivr.id==='name' && isListening")
    banks=page.request.get(args.base_url+'/v1/institutions?list=demo').json()
    if isinstance(banks,dict):banks=banks.get('institutions',banks.get('items',[]))
    bank=next(row for row in banks if 'eastern' in row['name_en'].lower())
    def response(route):
        content=route.request.post_data_buffer.decode('utf-8',errors='replace')
        assert 'ivr_step' in content
        data=[('transcript',{'text':'Eastern Bank','language':'en'}),('result',{'type':'report_card','institution_id':bank['id'],'text':'Synthetic sourced report routing'})]
        route.fulfill(content_type='text/event-stream',body=''.join('event: '+event+'\ndata: '+json.dumps(value)+'\n\n' for event,value in data))
    page.route('**/v1/voice',response)
    page.locator('#ivr-tap').dblclick(delay=150)
    page.wait_for_function("() => ivr.id==='next' && isListening")
    assert any(x['kind']=='report_card' for x in readouts)
    assert page.locator('#ivr-heard').inner_text().endswith('Eastern Bank')
    for command,kind in [('reasons','reasons'),('sources','sources')]:
        def action_response(route):
            route.fulfill(content_type='text/event-stream',body='event: result\ndata: '+json.dumps({'type':'ivr_action','ivr_action':command,'text':''})+'\n\n')
        page.unroute('**/v1/voice',response)
        page.route('**/v1/voice',action_response)
        page.locator('#ivr-tap').dblclick(delay=150)
        page.wait_for_function("() => ivr.id==='next' && isListening")
        assert any(x['kind']==kind for x in readouts)
        page.unroute('**/v1/voice',action_response)
        page.route('**/v1/voice',response)
    quiet()
    # Keyboard/assistive activation resolves one choice without physical tap counting.
    page.locator('#ivr-tap').focus();page.keyboard.press('Enter')
    page.wait_for_function("() => ivr.id==='next' && isListening")
    assert sum(x['kind']=='report_card' for x in readouts)==2
    # Ambiguous candidates are confirmed one at a time, never silently selected.
    quiet();page.evaluate("ivr.enter('name')")
    page.wait_for_function("() => ivr.id==='name' && isListening")
    other=next(row for row in banks if row['id']!=bank['id'])
    def ambiguous(route):
        route.fulfill(content_type='text/event-stream',body='event: result\ndata: '+json.dumps({'type':'clarify','candidates':[bank,other],'text':'Choose a bank'})+'\n\n')
    page.unroute('**/v1/voice',response);page.route('**/v1/voice',ambiguous)
    page.locator('#ivr-tap').dblclick(delay=150)
    page.wait_for_function("() => ivr.id==='confirm' && isListening")
    assert bank['name_en'] in page.locator('#ivr-question').inner_text()
    quiet();page.locator('#ivr-tap').dblclick(delay=150)
    page.wait_for_function("() => ivr.id==='confirm' && ivrCandidateIndex===1 && isListening")
    assert other['name_en'] in page.locator('#ivr-question').inner_text()
    assert any(x.get('prompt')=='ivr_confirm' and x['institution_id']==other['id'] for x in readouts)
    page.locator('#ivr-skip').click()
    assert page.locator('#ivr-overlay').is_hidden()
    assert page.evaluate("currentTab==='home' && !isListening && appSettings.ivrFinished")
    page.reload(wait_until='networkidle');page.locator('#ivr-overlay').wait_for(state='visible')
    page.locator('#settings-btn').click();page.locator('#settings-voiceonly').uncheck();page.locator('#settings-close').click()
    page.locator('#ivr-overlay').wait_for(state='hidden')
    assert page.locator('#ivr-overlay').is_hidden()
    page.reload(wait_until='networkidle');assert page.locator('#ivr-overlay').is_hidden()
    page.locator('#settings-btn').click();page.locator('#settings-voiceonly').check();page.locator('#settings-close').click()
    page.wait_for_function("() => ivr.id==='open' && ivr.phase==='waiting'")
    page.locator('#settings-btn').click();page.locator('#settings-motion').uncheck();page.locator('#settings-close').click()
    assert page.evaluate("ivr.id==='open'")

    for width,height in [(320,640),(844,390),(390,300),(1440,900)]:
        page.set_viewport_size({'width':width,'height':height})
        page.evaluate('startGuidedVoice()');page.locator('#ivr-overlay').wait_for(state='visible')
        bounds=page.locator('#ivr-skip').bounding_box();assert bounds and bounds['y']>=0 and bounds['y']+bounds['height']<=height
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('#ivr-skip').click()
    assert not errors,errors
    browser.close()
print('Synthetic guided browser flow passed: normal first load, explicit enable, permission, choices, recording, replay, saved enable/disable after reload, unrelated settings and viewport sizes.')
