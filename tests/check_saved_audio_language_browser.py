"""Saved Bangla loan playback from English UI; no live microphone/provider calls."""
import argparse
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',default='http://127.0.0.1:8029')
    args=parser.parse_args()
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(**p.devices['Pixel 7'],service_workers='block')
        context.add_init_script("localStorage.setItem('ilma-settings',JSON.stringify({language:'en',ivrFinished:true,micExplained:false,voiceonly:false}))")
        page=context.new_page();page.goto(args.base,wait_until='networkidle')
        page.locator('.dock [data-tab=services]').click()
        with page.expect_response(lambda r:'/v1/services/compare?' in r.url and 'home_loan' in r.url) as response:
            page.locator('[data-category=loan]').click()
        approved=response.value.json()['readout']['text']
        button=page.locator('#loan-listen');button.wait_for()
        assert 'Bangla' in button.inner_text()
        before=page.locator('#loan-amount').input_value()
        button.click()
        page.wait_for_function("()=>{const a=document.getElementById('ilma-player');return !a.paused&&a.currentTime>0.2}")
        assert page.locator('#loan-narration').text_content()==approved
        assert page.locator('#loan-narration').get_attribute('lang')=='bn'
        assert page.locator('#loan-audio-error').is_hidden()
        assert page.locator('#loan-amount').input_value()==before
        button.click()
        assert page.evaluate("document.getElementById('ilma-player').paused")
        assert 'Bangla' in button.inner_text()
        page.locator('#loan-amount').fill('4000000');button.click()
        assert page.evaluate("document.getElementById('ilma-player').paused")
        assert page.locator('#loan-narration').text_content()==approved
        assert page.locator('#loan-amount').input_value().replace(',','')=='4000000'
        assert page.locator('html').get_attribute('lang')=='en'
        print('PASS English UI: approved Bangla playback, exact transcript, Stop reset and edited amount suppression')
        context.close();browser.close()


if __name__=='__main__':main()
