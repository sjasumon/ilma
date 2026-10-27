"""Opt-in v5.4 retail-card/browser checks without microphone/provider calls."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url',default='http://127.0.0.1:8017')
parser.add_argument('--output',type=Path,default=Path('/tmp/ilma-services-v54'))
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':360,'height':640},service_workers='block')
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(args.base_url,wait_until='networkidle')
    for lang in ('bn','en'):
        page.evaluate('(lang)=>setLanguage(lang,false)',lang)
        page.locator('.dock [data-tab="services"]').click()
        page.locator('#service-search-mic svg').wait_for()
        page.locator('[data-category="card"]').click()
        page.locator('#compare-tier').select_option('Signature')
        page.wait_for_function("() => document.querySelector('#service-savings')?.textContent.includes('5,000')||document.querySelector('#service-savings')?.textContent.includes('৫,০০০')")
        assert page.locator('#comparison-rows > .catalog-offer-row').count()==9
        ebl=page.locator('#comparison-rows > article').filter(has=page.locator('[data-offer="svc-2731"]'))
        assert 'Signature Light / Women Signature' in ebl.inner_text()
        assert ebl.locator('details').count()==1
        ebl.locator('summary').click()
        assert 'Signature Exclusive' in ebl.inner_text()
        variant=ebl.locator('details [data-offer]')
        assert variant.is_visible()
        variant.click();page.locator('#offer-bank-report').wait_for()
        assert 'Signature Exclusive' in page.locator('#services-catalog h3').first.inner_text()
        offers=page.request.get(args.base_url+'/v1/services/offers/svc-2739').json()['offers']
        assert all(r['column_header']==offers[0]['column_header'] for r in offers)
        source=page.locator('#services-catalog [data-source]').first
        source_id=source.get_attribute('data-source')
        expected=next(r['quote'] for r in offers if r['offer_id']==source_id)
        source.click();assert page.locator('#modal-quote').inner_text().strip()==expected.strip()
        assert page.locator('#modal-quote mark').count()>0
        page.locator('#proof-modal-close').click()
        page.locator('#offer-back').click();page.locator('#compare-tier').select_option('Platinum')
        page.wait_for_function("() => document.querySelector('#compare-tier')?.value==='Platinum'&&document.querySelectorAll('.catalog-variants').length>1")
        brac=page.locator('#comparison-rows > article').filter(has_text='BRAC Bank PLC')
        assert brac.locator('details summary').count()==1
        brac.locator('summary').click()
        assert brac.locator('details [data-offer]').count()==2
        assert 'Platinum Flexi' in brac.inner_text() and 'TARA Platinum' in brac.inner_text()
        if lang=='bn':assert '১৫% ভ্যাট প্রযোজ্য' in brac.inner_text()
        assert 'Corporate' not in brac.inner_text() and 'RFCD' not in brac.inner_text()
        page.screenshot(path=str(args.output/f'platinum-variants-{lang}.png'),full_page=True)
        # Bank -> bank-specific services is a separate grouped product view.
        page.locator('.dock [data-tab="detail"]').click();page.locator('[data-bank="19"]').click()
        page.locator('[data-bank-detail="services"]').click();page.locator('[data-bank-offer]').first.wait_for()
        assert 'Signature Exclusive' in page.locator('#services-catalog').inner_text()
    page.set_viewport_size({'width':320,'height':640})
    page.evaluate("document.documentElement.style.fontSize='200%'")
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
print('v5.4 services UI passed: BN/EN main/variants, exact source sheets, exclusions, bank services, 200% text.')
