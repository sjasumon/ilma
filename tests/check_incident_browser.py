"""Opt-in bilingual incident UI checks against an imported test deployment."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:8017')
parser.add_argument('--output',type=Path,default=Path('/tmp/ilma-incidents-browser'))
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':360,'height':740},service_workers='block')
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(args.base_url,wait_until='networkidle')
    for language in ('bn','en'):
        page.evaluate('(lang)=>{setLanguage(lang,false);}',language)
        page.locator('.dock [data-tab="detail"]').click()
        page.locator('[data-bank="36"]').wait_for()
        assert page.locator('[data-bank]').count()==11
        assert page.locator('.catalog-status.high').count()==2
        page.locator('[data-bank="36"]').click()
        page.locator('[data-bank-detail="history"]').wait_for()
        page.screenshot(path=str(args.output/f'nbl-high-{language}.png'),full_page=True)
        assert page.locator('#card-status-word').inner_text()==('ঝুঁকি বেশি' if language=='bn' else 'High risk')
        page.locator('[data-bank-detail="history"]').click()
        page.locator('#incident-filter').wait_for()
        assert page.locator('#incident-rows article').count()==5
        assert page.locator('#incident-rows [data-source]').count()==8
        page.locator('#incident-filter').select_option('audit_warning')
        assert page.locator('#incident-rows article').count()==2
        page.locator('#incident-rows [data-source]').first.click()
        page.locator('#proof-modal-close').wait_for()
        page.locator('#proof-modal-close').click()
        page.screenshot(path=str(args.output/f'nbl-history-{language}.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('.dock [data-tab="detail"]').click()
        page.locator('[data-bank="26"]').click()
        page.locator('[data-bank-detail="health"]').click()
        page.locator('#bank-detail-body [data-source]').wait_for()
        assert ('খেলাপি ঋণ: তথ্য নেই' if language=='bn' else 'Bad loans: No data') in page.locator('#bank-detail-body').inner_text()
    for width,height in [(320,640),(740,360),(1440,900)]:
        page.set_viewport_size({'width':width,'height':height})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.set_viewport_size({'width':360,'height':740})
    page.evaluate("document.documentElement.style.fontSize='200%'")
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
print('Incident UI passed: BN/EN, two High cards, 11 banks, history filters/sources, missing NPL, phone/rotation/desktop.')
