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
