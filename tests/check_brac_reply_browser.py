"""Opt-in read-only browser check using typed ASR spellings, speech disabled."""
import argparse,re
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8018');args=p.parse_args()
with sync_playwright() as pw:
 browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true,micExplained:true,language:'bn',speak:false}))")
 page.goto(args.base_url,wait_until='networkidle')
 def reply(text,state):
  page.evaluate('(text)=>submitTextQuestion(text)',text)
  page.wait_for_function('(state)=>!isSearching&&agentConversation?.state===state',arg=state,timeout=5000)
 bank=None
 for alias in ['breakbank','break bank','ব্রেক ব্যাংক']:
  page.evaluate('resetAgentConversation()');reply(alias,'BANK')
  current=page.evaluate('agentConversation.institution_id');assert current and (bank is None or current==bank)
  bank=current
  assert 'ব্র্যাক' in page.locator('#agent-answer').inner_text()
  assert page.evaluate('currentLang')=='bn'
 for text in ['more details','more detals']:
  reply(text,'DETAIL')
  assert page.evaluate('agentConversation.language')=='bn' and page.evaluate('currentLang')=='bn'
  assert page.locator('html').get_attribute('lang')=='bn' and page.locator('#voice-language-chip').is_hidden()
  assert re.search('[\u0980-\u09ff]',page.locator('#agent-answer').inner_text())
  assert page.evaluate('agentConversation.institution_id')==bank
 reply('How is BRAC Bank doing?','BANK')
 assert page.evaluate('currentLang')=='en' and page.evaluate('agentConversation.language')=='en'
 page.evaluate("setLanguage('en',false)");page.evaluate('resetAgentConversation()')
 city=next(b['id'] for b in page.request.get(args.base_url.rstrip('/')+'/v1/institutions?list=demo').json() if b['slug']=='citybank')
 reply('How is Citibank doing?','ASK_BANK')
 assert page.evaluate('agentConversation.confirm_bank_id')==city and 'Bangladesh' in page.locator('#agent-answer').inner_text()
 page.locator('#agent-options button').filter(has_text='Yes').click();page.wait_for_function('()=>!isSearching&&agentConversation?.state==="BANK"')
 assert page.evaluate('agentConversation.institution_id')==city
 reply('How is Citibank doing?','ASK_BANK')
 page.locator('#agent-options button').filter(has_text='No').click();page.wait_for_function('()=>!isSearching&&agentConversation?.confirm_bank_id===null')
 assert page.evaluate('agentConversation.institution_id') is None
 assert not errors,errors
 browser.close()
print('BRAC reply browser passed: all three ASR aliases, canonical bank label, Bangla retained for exact/fuzzy scripted replies, and English detection for a genuine question. No microphone recording used.')
