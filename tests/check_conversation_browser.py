"""Opt-in local browser checks. Run against a preview with paid providers disabled."""
import argparse
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8018');args=p.parse_args()
with sync_playwright() as pw:
 browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true,micExplained:true,language:'en',speak:false}))")
 page.goto(args.base_url,wait_until='networkidle')
 def reply(text,state):
  page.evaluate('(text)=>submitTextQuestion(text)',text)
  try:page.wait_for_function('(state)=>!isSearching&&agentConversation?.state===state',arg=state,timeout=5000)
  except Exception:raise AssertionError((state,page.evaluate('()=>({currentTab,isSearching,conversation:agentConversation,feedback:document.getElementById("voice-feedback-message").textContent})'),errors)) from None
  assert page.locator('#agent-sentences').inner_text().strip()
 reply('ব্র্যাক ব্যাংক কেমন আছে','BANK');bank=page.evaluate('agentConversation.institution_id');assert bank
 assert page.evaluate('currentLang')=='bn'
 assert 'English-এ থাকুন' in page.locator('#voice-language-chip').inner_text()
 page.locator('#voice-language-chip').click();page.wait_for_function("()=>!isSearching&&agentConversation?.language==='en'")
 assert page.evaluate('currentLang')=='en' and page.evaluate('agentConversation.institution_id')==bank
 assert 'BRAC' in page.locator('#agent-sentences').inner_text()
 for text,state in [('আরও বিস্তারিত','DETAIL'),('ব্যাংকের সেবা','SERVICES'),('details','DETAIL'),('more details','DETAIL'),('এফডিআর রেট কত','SERVICE'),('আরও বিস্তারিত','DETAIL')]:
  previous=page.locator('#agent-question').inner_text();reply(text,state)
  assert page.evaluate('agentConversation.institution_id')==bank
  assert page.locator('#agent-sentences').inner_text().strip()!=previous.strip()
 reply('ঢাকা','DETAIL');assert page.locator('#agent-text-form').is_hidden()
 reply('ঢাকা','DETAIL');assert page.locator('#agent-text-form').is_visible()
 assert page.locator('#agent-text-input').evaluate('(el)=>document.activeElement===el')
 assert page.evaluate('agentConversation.institution_id')==bank and not page.evaluate('isListening')
 for width,height in [(320,640),(844,390),(390,300),(1440,900)]:
  page.set_viewport_size({'width':width,'height':height})
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert page.locator('.dock').bounding_box()['y']+page.locator('.dock').bounding_box()['height']<=height+1
 page.set_viewport_size({'width':390,'height':844});page.locator('#agent-text-input').fill('সেবা');page.locator('#agent-text-submit').click()
 page.wait_for_function("()=>!isSearching&&agentConversation?.state==='SERVICES'")
 assert page.locator('#agent-text-form').is_hidden() and page.evaluate('agentConversation.institution_id')==bank
 page.evaluate("document.documentElement.style.fontSize='200%'")
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors,errors
 browser.close()
print('Conversation browser passed: bilingual switch/undo, retained bank, cross-state commands, content replies, two-miss typing recovery/focus, keyboard/rotation/desktop/200% text. No microphone acceptance claimed.')
