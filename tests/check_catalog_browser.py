"""Opt-in live browser checks and screenshots; run separately from pytest."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:8001')
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'design/reviews')
args=parser.parse_args()
root=args.output
(root/'bank-tab').mkdir(parents=True,exist_ok=True)
(root/'bank-services').mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch()
 page=browser.new_page(viewport={'width':360,'height':640},service_workers='block')
 errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
 page.goto(args.base_url,wait_until='networkidle')
 def snap(folder,name):
  page.wait_for_timeout(350)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),name+' horizontal overflow'
  page.screenshot(path=str(root/folder/(name+'.png')),full_page=name!='source-sheet')
 page.locator('.dock [data-tab="detail"]').click();page.locator('[data-bank="19"]').wait_for()
 assert page.locator('[data-bank]').count()==11
 snap('bank-tab','B1-list')
 page.locator('#bank-list-search').fill('DBBL');assert page.locator('[data-bank]').count()==1
 assert page.locator('[data-bank="18"]').count()==1
 page.locator('#bank-list-search').fill('')
 page.locator('[data-bank="19"]').click();page.wait_for_function("() => document.getElementById('card-status-word').textContent==='ভালো অবস্থা'")
 snap('bank-tab','B2-EBL')
 page.locator('[data-bank-detail="health"]').click();page.locator('#bank-detail-body [data-source]').first.wait_for()
 snap('bank-tab','B3-health')
 page.locator('#bank-detail-body [data-source]').first.click();snap('bank-tab','source-sheet');page.locator('#proof-modal-close').click()
 page.locator('#bank-detail-back').click();page.locator('[data-bank-detail="rating"]').click();page.locator('#bank-detail-body [data-source]').first.wait_for();snap('bank-tab','B3-rating')
 page.locator('.dock [data-tab="detail"]').click();page.locator('[data-bank="48"]').click();page.wait_for_function("() => document.getElementById('card-status-word').textContent==='তথ্য কম'");snap('bank-tab','B2-SBAC')
 page.locator('.dock [data-tab="services"]').click();page.locator('[data-category="deposit"]').wait_for();snap('bank-services','S1-home')
 page.locator('[data-category="deposit"]').click();page.locator('#comparison-rows .catalog-offer-row').first.wait_for();snap('bank-services','S2-FDR-12M')
 page.locator('#services-back').click();page.locator('[data-category="card"]').click();page.locator('#compare-tier').select_option('Signature');page.wait_for_function("() => document.querySelector('#service-savings')?.textContent.includes('৫,০০০')")
 assert page.locator('.catalog-offer-row').count()==9
 snap('bank-services','S2-Visa-Signature')
 page.locator('[data-offer="svc-2239"]').click();page.locator('#offer-bank-report').wait_for();snap('bank-services','S3-card')
 page.locator('#services-catalog [data-source]').first.click();snap('bank-services','source-sheet');page.locator('#proof-modal-close').click()
 page.locator('.dock [data-tab="services"]').click();page.locator('[data-category="loan"]').click();page.locator('#comparison-example').wait_for();snap('bank-services','S2-home-loan')
 requests=[];page.on('request',lambda r:requests.append(r.url))
 page.locator('#comparison-example').select_option('500000');page.locator('#comparison-term').fill('180');page.wait_for_timeout(100)
 assert not requests,'Calculator input must not cause network requests'
 # Emulate 200% text enlargement without changing the screen's pixel width.
 page.evaluate("""() => { const els=[...document.querySelectorAll('h1,h2,h3,p,span,strong,small,button,label,input,select,a')];const sizes=els.map(el=>parseFloat(getComputedStyle(el).fontSize));els.forEach((el,i)=>el.style.fontSize=(sizes[i]*2)+'px'); }""")
 snap('bank-services','S2-home-loan-200pct')
 assert not errors,errors
 print('Live browser: B1/B2/B3, source sheets, S1/S2/S3, 200% text, nine rows and local-only calculator passed')
 page.close();browser.close()
