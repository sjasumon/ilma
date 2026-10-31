"""Browser smoke matrix against handwritten public fixtures; no DB or providers.

This serves repository assets, never a deployed service. It checks UI behavior,
not source accuracy, native phone audio, screen readers or WCAG conformance.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BANK = dict(id=1, slug='sample', name_bn='নমুনা ব্যাংক', name_en='Sample Bank',
            aliases=['Sample'], islamic=False,
            status=dict(code='no_data', label_bn='মূল্যায়ন করা হয়নি', label_en='Not rated'))
REPORT = dict(institution=BANK, status=BANK['status'], founded_year=1999,
              data_date='2026-10-01', reasons=[], checks=[], profile_facts=[],
              comparison_facts=[], section_counts={}, readout=dict(text='', audio_url=None))
CATEGORIES = [dict(category='card', choices=[['Visa', 'Gold']]),
              dict(category='loan'), dict(category='deposit'), dict(category='account_fee')]


def fixture(path, query):
    """Deliberately tiny synthetic data, without imported banking facts."""
    if path in ('/v1/institutions', '/v1/institutions/index'):
        return [BANK]
    if path == '/v1/institutions/1/report-card':
        return REPORT
    if path.endswith('/watch'):
        return dict(watching=False)
    if path == '/v1/content/fixed':
        return dict(available=False, reason='not_published', clips={})
    if path == '/v1/voice/config':
        return dict(enabled=False)
    if path == '/v1/services/audio-manifest':
        return dict(clips={})
    if path == '/v1/services/categories':
        return CATEGORIES
    if path == '/v1/services/accounts':
        return dict(choice=dict(product_type='account_fee', item=query.get('item', ['savings'])[0],
                                audience=query.get('audience', ['all'])[0]),
                    banks=[], readouts={}, deposit_readouts={})
    if path == '/v1/services/deposits':
        return dict(choice=dict(product_type=query.get('product_type', ['fdr'])[0]),
                    catalog_banks=[], readouts={}, insurance=None)
    if path == '/v1/services/compare':
        kind = query.get('product_type', ['home_loan'])[0]
        return dict(choice=dict(product_type=kind, attribute='annual_fee', network='Visa', tier='Gold'),
                    rows=[], readout=None, sort='lower_cost_first')
    if path in ('/v1/news', '/v1/extra-news'):
        return []
    return None


class FixtureServer(ThreadingHTTPServer):
    daemon_threads = True
    failed_catalog = False
    posts = []
    late_bundle_gate = None
    offline_api = False
    requests = []


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == '/static/js/bank-services-ui.js' and self.server.late_bundle_gate is not None:
            self.server.late_bundle_gate.wait(timeout=15)
        if url.path.startswith('/v1/'):
            self.server.requests.append(self.path)
            if self.server.offline_api:
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            data = fixture(url.path, parse_qs(url.query))
            if self.server.failed_catalog == 'network' and url.path == '/v1/services/deposits':
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            if self.server.failed_catalog and url.path == '/v1/services/deposits':
                self.send_response(503)
                self.end_headers()
                return
            body = json.dumps(data if data is not None else {}, ensure_ascii=False).encode()
            self.send_response(200 if data is not None else 404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if url.path == '/':
            self.path = '/static/index.html'
        elif url.path == '/sw.js':
            self.path = '/static/sw.js'
        super().do_GET()

    def end_headers(self):
        self.send_header('Service-Worker-Allowed', '/')
        super().end_headers()

    def do_POST(self):
        self.server.posts.append(urlsplit(self.path).path)
        self.send_response(503)
        self.end_headers()


SETTINGS = "localStorage.setItem('ilma-settings',JSON.stringify({ivrFinished:true,micExplained:false,voiceonly:false}))"


def goto_services(page):
    page.locator('.dock [data-tab=services]').click()
    page.locator('[data-category=loan]').wait_for()


def dialogs(page):
    for category, prefix in [('loan', 'loan'), ('deposit', 'deposit'), ('account_fee', 'account'), ('card', 'card')]:
        goto_services(page)
        page.locator('[data-category='+category+']').click()
        opener = page.locator('#'+prefix+'-meanings')
        opener.click()
        dialog = page.get_by_role('dialog')
        assert dialog.count() == 1
        heading = dialog.get_attribute('aria-labelledby')
        assert heading and page.locator('#'+heading).inner_text().strip(), 'Dialog needs an accessible name'
        assert dialog.evaluate("e=>{const c=getComputedStyle(e).backgroundColor;return c!=='transparent'&&!c.endsWith(', 0)')}"), 'Dialog must have an opaque surface'
        close = page.locator('#'+prefix+'-meaning-close')
        contrast = close.evaluate('''e=>{
          const style=getComputedStyle(e);
          const luminance=color=>color.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
          const text=luminance(style.color),background=luminance(style.backgroundColor);
          return (Math.max(text,background)+.05)/(Math.min(text,background)+.05);
        }''')
        assert contrast >= 4.5, 'Normal-size close text needs sufficient contrast'
        close.click()
        assert opener.evaluate('e=>e===document.activeElement'), 'Close must restore opener focus'


def navigation(page, server):
    page.locator('.dock [data-tab=detail]').click()
    search = page.locator('#bank-list-search')
    search.fill('sample')
    with page.expect_response(lambda r: urlsplit(r.url).path == '/v1/institutions/1/watch') as watch:
        page.locator('[data-bank]').click()
    assert watch.value.json() == {'watching': False}
    page.locator('#card-bank-name').get_by_text('নমুনা ব্যাংক', exact=True).wait_for()
    page.wait_for_load_state('networkidle')
    report_url = page.url
    assert 'screen=report' in report_url
    page.go_back()
    search.wait_for()
    assert search.input_value() == 'sample'
    with page.expect_response(lambda r: urlsplit(r.url).path == '/v1/institutions/1/watch') as watch:
        page.go_forward()
    assert watch.value.json() == {'watching': False}
    page.locator('#bank-report-view').wait_for()
    page.locator('#bank-list-back').click()
    search.wait_for()
    assert search.input_value() == 'sample'
    with page.expect_response(lambda r: urlsplit(r.url).path == '/v1/institutions/1/watch') as watch:
        page.goto(report_url)
    assert watch.value.json() == {'watching': False}
    with page.expect_response(lambda r: urlsplit(r.url).path == '/v1/institutions/1/watch') as watch:
        page.reload(wait_until='networkidle')
    assert watch.value.json() == {'watching': False}
    page.locator('#bank-report-view').wait_for()
    assert page.locator('#card-bank-name').inner_text() == 'নমুনা ব্যাংক'
    goto_services(page)
    page.locator('[data-category=loan]').click()
    amount = page.locator('#loan-amount')
    amount.fill('1234567')
    assert '1234567' not in page.url
    assert '1234567' not in page.evaluate('JSON.stringify(history.state)')
    page.go_back()
    page.locator('[data-category=loan]').wait_for()
    page.go_forward()
    amount.wait_for()
    assert amount.input_value().replace(',', '') in ('1234567', '১২৩৪৫৬৭')
    assert not any('1234567' in path for path in server.requests), 'Calculator inputs must never be sent'


def navigation_race(page):
    page.locator('.dock [data-tab=detail]').click()
    with page.expect_response(lambda r:urlsplit(r.url).path.endswith('/watch')) as watch:
        page.locator('[data-bank]').click()
    watch.value.json()
    goto_services(page)
    held=[]
    page.context.route('**/report-card',lambda r:held.append(r),times=1)
    page.go_back()
    for _ in range(200):
        if held:break
        page.wait_for_timeout(10)
    assert held, 'Restore should be waiting for the held report'
    goto_services(page)
    assert 'screen=services' in page.url
    with page.expect_response(lambda r:r.url.endswith('/report-card')) as report:
        held[0].continue_()
    report.value.json()
    assert 'screen=services' in page.url
    page.locator('[data-category=loan]').wait_for()


def retry(page, server):
    # Block workers for this journey: an uncached failure must retry its own view.
    server.failed_catalog = 'network'
    goto_services(page)
    page.locator('[data-category=deposit]').click()
    page.locator('[data-retry]').wait_for()
    text = page.locator('#services-catalog').inner_text()
    assert 'Failed to fetch' not in text and 'Load failed' not in text
    server.failed_catalog = False
    page.locator('[data-retry]').click()
    page.locator('#deposit-amount').wait_for()
    assert 'screen=compare' in page.url


def large_text(page):
    goto_services(page)
    page.locator('[data-category=account_fee]').click()
    page.locator('#account-balance').wait_for()
    # Twice the 14px base text, independent of OS font-scale controls.
    page.evaluate("document.documentElement.style.setProperty('--fs','28px')")
    assert page.locator('#main-content').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
    for item in page.locator('#services-catalog input').all():
        assert item.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)') >= 16


def orientation(page, mobile):
    if not mobile:
        return
    page.evaluate("""() => {
      window.testOrientation={type:'portrait-primary'};
      Object.defineProperty(screen,'orientation',{configurable:true,get:()=>window.testOrientation});
      window.dispatchEvent(new Event('orientationchange'));
    }""")
    assert page.locator('#orientation-panel').is_hidden()
    viewport = page.viewport_size
    page.set_viewport_size(dict(width=viewport['width'], height=300))
    assert page.locator('#orientation-panel').is_hidden(), 'Portrait keyboard resize must not trigger rotate panel'
    page.set_viewport_size(viewport)
    page.evaluate("window.testOrientation.type='landscape-primary';window.dispatchEvent(new Event('orientationchange'))")
    page.locator('#orientation-panel').wait_for()
    assert page.locator('.scr').evaluate('e=>e.inert')
    page.evaluate("window.testOrientation.type='portrait-primary';window.dispatchEvent(new Event('orientationchange'))")
    assert page.locator('#orientation-panel').is_hidden()


def offline(browser, profile, base, output, server):
    """Exercise CacheStorage/SW by dropping transport, without offline-emulator quirks."""
    context = browser.new_context(**profile)
    context.add_init_script(SETTINGS)
    page = context.new_page()
    failures = []
    page.on('pageerror', lambda error: failures.append(str(error)))
    paths = [('/v1/services/deposits?product_type=fdr&audience=all&basis=conventional', 'deposit', '#deposit-amount'),
             ('/v1/services/accounts?product_type=account_fee&item=savings&audience=all', 'account_fee', '#account-balance')]
    try:
        page.goto(base, wait_until='networkidle')
        page.wait_for_function('()=>!!navigator.serviceWorker.controller', timeout=15000)
        for path, category, selector in paths:
            goto_services(page)
            page.locator('[data-category='+category+']').click()
            page.locator(selector).wait_for()
            page.wait_for_function("""async path => {
              for(const name of await caches.keys())if(name.startsWith('ilma-public-banks-')){
                const response=await (await caches.open(name)).match(path);
                if(response)return !!response.headers.get('X-ILMA-Cached-At');
              }
              return false;
            }""", arg=path)
        # Temporary service failure must retain the warmed screen as well.
        server.failed_catalog = True
        goto_services(page)
        page.locator('[data-category=deposit]').click()
        page.locator('#deposit-amount').wait_for()
        page.locator('.catalog-offline').wait_for()
        server.failed_catalog = False
        server.offline_api = True
        for path, category, selector in paths:
            goto_services(page)
            page.locator('[data-category='+category+']').click()
            page.locator(selector).wait_for()
            page.locator('.catalog-offline').wait_for()
            cached = page.evaluate("""async path => {
              const response=await fetch(path);
              return {status:response.status,offline:response.headers.get('X-ILMA-Offline'),saved:response.headers.get('X-ILMA-Cached-At')};
            }""", path)
            assert cached['status']==200 and cached['offline']=='1' and cached['saved']
        assert not failures, failures
    except Exception:
        page.screenshot(path=str(output/'offline-failure.png'), full_page=True)
        raise
    finally:
        server.offline_api = False
        server.failed_catalog = False
        context.close()


def readiness(browser, profile, base, output, server):
    """The primary action must not look ready while a late bundle is held."""
    gate = threading.Event()
    server.late_bundle_gate = gate
    context = browser.new_context(**profile, service_workers='block')
    context.add_init_script(SETTINGS)
    page = context.new_page()
    failures = []
    page.on('pageerror', lambda error: failures.append(str(error)))
    try:
        page.goto(base, wait_until='commit')
        target = page.locator('#home-tap-target')
        target.wait_for()
        assert page.evaluate('document.readyState') == 'loading'
        assert target.is_disabled(), 'Visible primary action must be disabled until bound'
        assert target.get_attribute('aria-busy') == 'true'
        page.locator('#home-loading').wait_for()
        gate.set()
        page.wait_for_load_state('networkidle')
        assert target.is_enabled()
        assert page.locator('#home-loading').is_hidden()
        target.click()
        page.locator('#mic-permission-dialog').wait_for()
        assert not failures, failures
    except Exception:
        page.screenshot(path=str(output/'readiness-failure.png'), full_page=True)
        raise
    finally:
        gate.set()
        server.late_bundle_gate = None
        context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=['android', 'iphone', 'desktop'], required=True)
    parser.add_argument('--output', type=Path, default=Path('/tmp/ilma-browser-smoke'))
    parser.add_argument('--check-retry', action='store_true')
    parser.add_argument('--check-readiness', action='store_true')
    parser.add_argument('--check-offline', action='store_true')
    args = parser.parse_args()
    output = args.output/args.profile
    output.mkdir(parents=True, exist_ok=True)
    server = FixtureServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:'+str(server.server_port)+'/'
    try:
        with sync_playwright() as p:
            engine = p.webkit if args.profile == 'iphone' else p.chromium
            profile = p.devices['iPhone 13'] if args.profile == 'iphone' else p.devices['Pixel 7'] if args.profile == 'android' else dict(viewport=dict(width=1440, height=900))
            browser = engine.launch()
            context = browser.new_context(**profile, service_workers='block')
            context.add_init_script(SETTINGS)
            page = context.new_page()
            failures = []
            page.on('pageerror', lambda error: failures.append(str(error)))
            check = 'startup'
            try:
                page.goto(base, wait_until='networkidle')
                for check, function in [('dialogs', lambda: dialogs(page)), ('navigation', lambda: (navigation(page, server),navigation_race(page))), ('large-text', lambda: large_text(page)), ('orientation', lambda: orientation(page, args.profile != 'desktop'))]:
                    function()
                    print('PASS', args.profile, check, flush=True)
                if args.check_retry:
                    check = 'retry'
                    retry(page, server)
                    print('PASS', args.profile, check, flush=True)
                assert not failures, failures
                assert not server.posts, 'Smoke tests must never invoke provider/voice POSTs'
                page.screenshot(path=str(output/'passed.png'), full_page=True)
            except Exception:
                page.screenshot(path=str(output/(check+'-failure.png')), full_page=True)
                (output/'failure.txt').write_text('\n'.join(failures))
                raise
            finally:
                context.close()
            try:
                if args.check_offline:
                    offline(browser, profile, base, output, server)
                    print('PASS', args.profile, 'offline', flush=True)
                if args.check_readiness:
                    readiness(browser, profile, base, output, server)
                    print('PASS', args.profile, 'readiness', flush=True)
                assert not server.posts, 'Smoke tests must never invoke provider/voice POSTs'
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
