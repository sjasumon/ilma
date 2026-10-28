"""Opt-in extra-publication UI checks; only a temporary anonymous watch changes."""
from pathlib import Path
import argparse
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8018');p.add_argument('--output',type=Path,default=Path('/tmp/ilma-extra-browser'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
with sync_playwright() as playwright:
 browser=playwright.chromium.launch()
 page=browser.new_page(viewport={'width':360,'height':640},service_workers='block')
 errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
 page.goto(a.base_url,wait_until='networkidle')
 for lang in ('bn','en'):
  page.evaluate('(lang)=>setLanguage(lang,false)',lang)
  page.locator('.dock [data-tab="detail"]').click();page.locator('[data-bank="19"]').click()
  for kind in ('announcements','reports','bb-notices'):
   page.locator(f'[data-bank-detail="{kind}"]').click();page.locator('#bank-detail-body .publication-card').first.wait_for()
   links=page.locator('#bank-detail-body .publication-card a');assert links.count()>0
   assert all(links.nth(i).get_attribute('href').startswith(('https://','http://')) for i in range(links.count()))
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   if page.locator('[data-more]').count():
    count=page.locator('.publication-card').count();page.locator('[data-more]').click();page.wait_for_function('(n)=>document.querySelectorAll(".publication-card").length>n',arg=count)
   page.screenshot(path=str(a.output/f'EBL-{kind}-{lang}.png'),full_page=True)
   page.locator('#bank-detail-back').click();page.locator('[data-bank-detail="health"]').wait_for()
  # UI saves/deletes one anonymous watch; no message or external notification.
  page.locator('#btn-watch-bank').wait_for(state='visible');page.wait_for_function('()=>!document.querySelector("#btn-watch-bank").disabled')
  watching=page.locator('#btn-watch-bank').get_attribute('aria-pressed')=='true'
  if not watching:page.locator('#btn-watch-bank').click();page.wait_for_function('()=>document.querySelector("#btn-watch-bank").getAttribute("aria-pressed")==="true"')
  page.locator('.dock [data-tab="news"]').click();page.locator('#extra-news-sections .publication-card').first.wait_for()
  assert page.locator('#extra-news-sections section').count()==3
  watched=page.locator('#extra-news-sections section').nth(2);assert watched.locator('.publication-card').count()>0
  assert ('Eastern Bank' in watched.inner_text() if lang=='en' else 'ইস্টার্ন' in watched.inner_text())
  page.screenshot(path=str(a.output/f'news-{lang}.png'),full_page=True)
  if not watching:
   page.locator('.dock [data-tab="detail"]').click();page.locator('[data-bank="19"]').click();page.locator('#btn-watch-bank').wait_for(state='visible');page.wait_for_function('()=>!document.querySelector("#btn-watch-bank").disabled')
   page.locator('#btn-watch-bank').click();page.wait_for_function('()=>document.querySelector("#btn-watch-bank").getAttribute("aria-pressed")==="false"')
 page.locator('.dock [data-tab="detail"]').click();page.locator('[data-bank="19"]').click();page.locator('[data-bank-detail="reports"]').click();page.locator('.publication-card').first.wait_for()
 for width,height in [(320,640),(640,360),(1440,900)]:
  page.set_viewport_size({'width':width,'height':height});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.set_viewport_size({'width':360,'height':640});page.evaluate('document.documentElement.style.fontSize="200%"')
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors,errors
 browser.close()
print('Extra-data browser passed: BN/EN bank pages, pagination, sources, watched news, cleanup, 200% text and viewports.')
