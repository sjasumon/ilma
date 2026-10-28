"""Opt-in geometry regression: app chrome stays visible around scrolling content."""
from pathlib import Path
import argparse
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8018');parser.add_argument('--output',type=Path,default=Path('/tmp/ilma-app-frame'));args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
GEOMETRY='''()=>{const r=s=>{const b=document.querySelector(s).getBoundingClientRect();return {top:b.top,bottom:b.bottom,left:b.left,right:b.right}};const m=document.querySelector('main');return {header:r('header'),dock:r('.dock'),main:r('main'),h:innerHeight,w:innerWidth,documentHeight:document.scrollingElement.scrollHeight,documentTop:document.scrollingElement.scrollTop,contentTop:m.scrollTop,contentHeight:m.scrollHeight,clientHeight:m.clientHeight}}'''
with sync_playwright() as p:
 browser=p.chromium.launch()
 page=browser.new_page(viewport={'width':390,'height':844},service_workers='block')
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(args.base_url,wait_until='networkidle')
 def verify(label):
  before=page.evaluate(GEOMETRY)
  assert before['header']['top']>=0 and before['dock']['bottom']<=before['h']+.5,(label,before)
  assert before['main']['top']>=before['header']['bottom']-.5 and before['main']['bottom']<=before['dock']['top']+.5,(label,before)
  assert before['documentHeight']<=before['h']+1 and before['documentTop']==0,(label,before)
  assert before['dock']['left']>=0 and before['dock']['right']<=before['w']+.5,(label,before)
  page.evaluate("document.querySelector('main').scrollTop=document.querySelector('main').scrollHeight")
  after=page.evaluate(GEOMETRY)
  assert abs(before['header']['top']-after['header']['top'])<1 and abs(before['dock']['top']-after['dock']['top'])<1,(label,before,after)
  if before['contentHeight']>before['clientHeight']+1:assert after['contentTop']>0,(label,after)
  for button in page.locator('.dock button').all():
   assert button.evaluate('el=>{const b=el.getBoundingClientRect();return el.contains(document.elementFromPoint(b.x+b.width/2,b.y+b.height/2))}'),label+' obstructed tab'
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),label+' horizontal overflow'
 for lang in ('bn','en'):
  page.evaluate('(lang)=>setLanguage(lang,false)',lang)
  for tab in ('home','services','detail','news'):
   page.locator(f'.dock [data-tab="{tab}"]').click();page.wait_for_timeout(350)
   if tab=='home':page.evaluate("{const p=document.createElement('div');p.id='frame-stress';p.style.minHeight='1600px';p.textContent='Layout test';document.querySelector('#tab-home').appendChild(p)}")
   verify(lang+' '+tab)
   page.screenshot(path=str(args.output/f'{tab}-{lang}.png'))
   if tab=='home':page.evaluate("document.getElementById('frame-stress').remove()")
   page.locator('.dock [data-tab="home"]').click()
   assert page.evaluate("document.querySelector('main').scrollTop")==0,'tab switch must reset content scroll'
  page.locator('.dock [data-tab="services"]').click();page.locator('[data-category="card"]').click();page.locator('#compare-tier').wait_for()
  verify(lang+' comparison')
  page.locator('#services-back').click();assert page.evaluate("document.querySelector('main').scrollTop")==0,'inner navigation must reset scroll'
 for width,height in [(320,640),(390,300),(844,390),(1440,900)]:
  page.set_viewport_size({'width':width,'height':height});verify(f'{width}x{height}')
 page.set_viewport_size({'width':360,'height':740});page.evaluate("document.documentElement.style.fontSize='200%'");verify('200 percent text')
 assert not errors,errors
 browser.close()
print('App frame passed: header/dock positions, every tab after scrolling, nested navigation, BN/EN, keyboard-size viewport, desktop and 200% text.')
