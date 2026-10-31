"""Read-only preview browser checks; no microphone or paid provider calls."""
import argparse
from playwright.sync_api import sync_playwright


def dialogs(page):
    page.locator('.dock [data-tab=services]').click()
    for category, prefix in [('loan', 'loan'), ('deposit', 'deposit'), ('account_fee', 'account'), ('card', 'card')]:
        page.locator('[data-category='+category+']').click()
        opener=page.locator('#'+prefix+'-meanings');opener.wait_for();opener.click()
        dialog=page.get_by_role('dialog');assert dialog.count()==1
        assert dialog.get_attribute('aria-labelledby')
        assert dialog.evaluate("e=>getComputedStyle(e).backgroundColor")=='rgb(13, 48, 44)'
        close=page.locator('#'+prefix+'-meaning-close')
        assert close.evaluate("e=>getComputedStyle(e).color")=='rgb(246, 240, 228)'
        close.click();assert opener.evaluate('e=>e===document.activeElement')
        page.locator('.dock [data-tab=services]').click()


def navigation(page):
    page.locator('.dock [data-tab=detail]').click()
    search=page.locator('#bank-list-search');search.wait_for();search.fill('eastern')
    row=page.locator('[data-bank]').first;row.click()
    page.locator('#bank-profile-chips').get_by_text('১৯৯২',exact=False).wait_for()
    report_url=page.url
    assert 'screen=report' in report_url
    page.go_back();search.wait_for();assert search.input_value()=='eastern'
    page.go_forward();page.locator('#bank-report-view').wait_for()
    page.locator('#bank-list-back').click();search.wait_for();assert search.input_value()=='eastern'
    page.locator('.dock [data-tab=services]').click();page.locator('[data-category=loan]').click()
    page.locator('#loan-amount').wait_for();page.locator('#loan-amount').fill('1234567')
    assert '1234567' not in page.url
    assert '1234567' not in page.evaluate('JSON.stringify(history.state)')
    page.go_back();page.locator('[data-category=loan]').wait_for()
    page.go_forward();page.locator('#loan-amount').wait_for()
    assert page.locator('#loan-amount').input_value().replace(',','') in ('1234567','১২৩৪৫৬৭')
    page.locator('.dock [data-tab=services]').click();page.locator('[data-category=account_fee]').click()
    page.locator('[data-account-audience=women]').click()
    page.locator('[data-account-detail]').first.click()
    page.locator('#account-detail-back').click()
    page.locator('[data-account-audience=women][aria-pressed=true]').wait_for()
    page.goto(report_url);page.locator('#bank-report-view').wait_for()
    page.locator('#bank-profile-chips').get_by_text('১৯৯২',exact=False).wait_for()


def fixed_audio(page):
    response=page.request.get(page.url.split('#')[0]+'v1/content/fixed')
    assert response.status==200
    assert response.json()['available'] is False
    assert response.json()['reason']=='not_published'
    page.locator('#settings-btn').click()
    page.locator('#settings-fixed-audio').wait_for()
    assert 'অডিও' in page.locator('#settings-fixed-audio').inner_text()
    page.locator('#settings-close').click()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='http://127.0.0.1:8027');parser.add_argument('--engine',choices=['chromium','webkit','all'],default='all');parser.add_argument('--check',default='dialogs');args=parser.parse_args()
    with sync_playwright() as p:
        for engine,device in [('chromium','Pixel 7'),('webkit','iPhone 13')]:
            if args.engine not in ('all',engine):continue
            browser=getattr(p,engine).launch();context=browser.new_context(**p.devices[device]);context.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true,micExplained:false,voiceonly:false}))")
            page=context.new_page();page.goto(args.base,wait_until='networkidle')
            globals()[args.check](page)
            print('PASS',engine,args.check,flush=True);context.close();browser.close()

if __name__=='__main__':main()
