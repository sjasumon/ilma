"""Opt-in browser checks; no microphone or paid-provider request is made."""
from playwright.sync_api import sync_playwright
import json,time,argparse
from urllib.parse import urlsplit
from pathlib import Path
parser=argparse.ArgumentParser(description='Opt-in browser checks for the website review; uses a temporary anonymous watch entry and removes it.')
parser.add_argument('--base-url',default='http://127.0.0.1:8001')
parser.add_argument('--baseline-url')
parser.add_argument('--output',type=Path,default=Path('/tmp/ilma-website-review'))
args=parser.parse_args()
out=args.output;out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch()
 for label,base_url in ([('before',args.baseline_url)] if args.baseline_url else [])+[('after',args.base_url.rstrip('/'))]:
  ctx=browser.new_context(viewport={'width':390,'height':844},service_workers='block')
  page=ctx.new_page();requests=[];errors=[];page.on('request',lambda r:requests.append(r.url));page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  start=time.monotonic();page.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true}))");page.goto(base_url,wait_until='networkidle');page.evaluate('document.fonts.ready')
  print(json.dumps({'version':label,'network_idle_seconds':round(time.monotonic()-start,2),'requests':len(requests),'external_requests':sum(urlsplit(r).netloc!=urlsplit(base_url).netloc for r in requests),'errors':errors}),flush=True)
  if label=='before':ctx.close();continue
  assert not errors,errors
  page.screenshot(path=str(out/'home.png'))
  page.locator('.dock [data-tab="detail"]').click();page.locator('[data-bank="19"]').wait_for();assert page.locator('#bank-list-mic svg').count()==1
  page.locator('#lang-btn').click();page.locator('[data-bank="19"]').wait_for()
  assert page.locator('[data-bank="19"] small').count()==0
  assert page.locator('.dock [data-tab="services"] span').inner_text()=='Services'
  page.locator('[data-bank="19"]').click();page.locator('#card-insurance-line a').wait_for()
  assert '2 lakh' in page.locator('#card-insurance-line').inner_text()
  page.screenshot(path=str(out/'bank-report-en.png'),full_page=True)
  page.locator('#btn-watch-bank').click();page.wait_for_function("() => document.getElementById('watch-notice').textContent.includes('none will be sent')")
  page.locator('#btn-watch-bank').click();page.wait_for_function("() => document.getElementById('btn-watch-bank').getAttribute('aria-pressed')==='false'")
  page.locator('#lang-btn').click()
  page.locator('.dock [data-tab="services"]').click();page.locator('[data-category="deposit"]').click();page.locator('.catalog-offer-row').first.wait_for()
  assert page.locator('#comparison-amount').count()==0
  assert page.locator('#comparison-example option').count()==4
  assert page.locator('.catalog-unverified').count()==1
  assert 'অবস্থা যাচাই হয়নি' in page.locator('.catalog-unverified').inner_text()
  assert 'Fixed Deposit' not in page.locator('#comparison-rows').inner_text()
  assert 'amount below' not in page.locator('#comparison-rows').inner_text()
  requests.clear();page.locator('#comparison-example').select_option('500000');page.wait_for_timeout(100);assert not requests
  page.screenshot(path=str(out/'fdr-bn.png'),full_page=True)
  offer_id=page.locator('[data-offer]').first.get_attribute('data-offer'); expected=page.request.get(f'{base_url}/v1/services/offers/{offer_id}').json()['offers'][0]['quote']; page.locator('[data-offer]').first.click();page.locator('#offer-bank-report').wait_for();page.locator('#services-catalog [data-source]').first.click();assert page.locator('#modal-quote').inner_text().strip()==expected.strip();page.screenshot(path=str(out/'source-sheet.png'));page.locator('#proof-modal-close').click()
  page.locator('.dock [data-tab="news"]').click();page.locator('#news-feed [role="listitem"]').first.wait_for()
  cards=page.locator('#news-feed [role="listitem"]');assert cards.count()>0
  for i in range(cards.count()):
   card=cards.nth(i);assert card.inner_text().count('খবরে প্রকাশিত, নিশ্চিত নয়')==1
   assert 'খবরটি ইংরেজিতে' in card.inner_text()
  page.screenshot(path=str(out/'news-bn.png'),full_page=True)
  assert not errors,errors
  print('After: names, services tab, fixed examples/no requests, warning, source, watch and news passed',flush=True)
  ctx.close()
 # Actual device metrics emulate physical rotation, including screen orientation.
 ctx=browser.new_context(viewport={'width':844,'height':390},screen={'width':844,'height':390},has_touch=True,is_mobile=True,service_workers='block')
 page=ctx.new_page();cdp=ctx.new_cdp_session(page);cdp.send('Emulation.setDeviceMetricsOverride',{'width':844,'height':390,'deviceScaleFactor':1,'mobile':True,'screenWidth':844,'screenHeight':390,'screenOrientation':{'type':'landscapePrimary','angle':90}})
 page.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true}))");page.goto(base_url,wait_until='networkidle');page.locator('#orientation-panel').wait_for(state='visible');assert page.locator('.scr').evaluate('(el)=>el.inert')
 page.screenshot(path=str(out/'landscape.png'))
 cdp.send('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True,'screenWidth':390,'screenHeight':844,'screenOrientation':{'type':'portraitPrimary','angle':0}});page.locator('#orientation-panel').wait_for(state='hidden');assert not page.locator('.scr').evaluate('(el)=>el.inert')
 # A software keyboard can shorten a portrait viewport without rotating the screen.
 cdp.send('Emulation.setDeviceMetricsOverride',{'width':390,'height':300,'deviceScaleFactor':1,'mobile':True,'screenWidth':390,'screenHeight':844,'screenOrientation':{'type':'portraitPrimary','angle':0}});assert page.locator('#orientation-panel').is_hidden()
 ctx.close()
 ctx=browser.new_context(viewport={'width':1366,'height':768},service_workers='block');page=ctx.new_page();page.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true}))");page.goto(base_url,wait_until='networkidle');assert page.locator('#orientation-panel').is_hidden();assert page.locator('.scr').bounding_box()['width']<600;ctx.close()
 browser.close()
 print('Rotation: touch landscape, return to portrait, keyboard and desktop passed',flush=True)
