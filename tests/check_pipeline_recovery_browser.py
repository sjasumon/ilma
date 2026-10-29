"""Opt-in read-only browser recovery checks; use a provider-disabled preview."""
import argparse
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8018');args=p.parse_args()
with sync_playwright() as pw:
 browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true,micExplained:true,language:'bn',speak:false}))")
 page.goto(args.base_url,wait_until='networkidle')
 def settled(state):page.wait_for_function('(state)=>!isSearching&&agentConversation?.state===state',arg=state)
 page.evaluate("submitTextQuestion('প্রাইম ব্যাংক')");settled('BANK');bank=page.evaluate('agentConversation.institution_id')
 page.evaluate("sendAgentChoice('detail')");settled('DETAIL')
 for state in ['DETAIL','FIGURES']:
  if state=='FIGURES':page.evaluate("submitTextQuestion('নিট মুনাফা কত')");settled(state)
  answer=page.locator('#agent-answer').inner_text();ids=page.evaluate('agentPanel.result.speech_fact_ids')
  page.locator('#agent-repeat').click();settled(state)
  assert page.locator('#agent-answer').inner_text()==answer
  assert page.evaluate('agentPanel.result.speech_fact_ids')==ids
 page.evaluate("sendAgentChoice('proof')");page.locator('#proof-modal.open').wait_for()
 assert page.evaluate("agentPanel.phase==='waiting'&&!isListening&&agentConversation.last_tool==='bank_figures'")
 page.locator('#proof-modal-close').click();page.locator('#agent-repeat').click();settled('FIGURES')
 assert page.locator('#agent-answer').inner_text()==answer
 page.evaluate("showVoiceFallback('no_speech')");assert page.locator('#agent-text-form').is_hidden()
 page.evaluate("showVoiceFallback('no_speech')");assert page.locator('#agent-text-form').is_visible()
 assert page.locator('#agent-text-input').evaluate('(el)=>document.activeElement===el')
 assert not page.evaluate('isListening')
 page.locator('#agent-text-input').fill('অর্থহীনশব্দ');page.locator('#agent-text-submit').click();page.wait_for_function('()=>!isSearching&&agentConversation.misses===1')
 assert page.locator('#agent-text-form').is_visible() and not page.evaluate('isListening')
 page.locator('#agent-text-input').fill('সেবা');page.locator('#agent-text-submit').click();settled('SERVICES')
 assert page.locator('#agent-text-form').is_hidden() and page.evaluate('agentConversation.institution_id')==bank
 page.evaluate("showVoiceFallback('voice_timeout')");assert page.locator('#agent-text-form').is_visible()
 assert not errors,errors
 browser.close()
print('Pipeline recovery browser passed: exact detail/figure repeat, source action without mic, two no-speech failures and hard failure typing, typed recovery with retained bank. No provider or physical microphone call.')
