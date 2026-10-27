"""Opt-in bounded read smoke test; not a production capacity benchmark.

No provider calls or POSTs. Run against your own ILMA deployment only.
"""
import argparse
import asyncio
import json
import math
import statistics
import time
import httpx


async def check(base_url):
    routes = ['/v1/health', '/v1/institutions?list=demo',
        '/v1/services/compare?product_type=card&network=Visa&tier=Signature']
    semaphore = asyncio.Semaphore(3)
    async with httpx.AsyncClient(base_url=base_url, timeout=10, follow_redirects=False) as client:
        async def request(number):
            async with semaphore:
                started = time.monotonic()
                try:
                    response = await client.get(routes[number % len(routes)])
                    healthy = response.status_code == 200
                    if number % len(routes) == 0:
                        healthy = healthy and response.json().get('ok') is True
                except (httpx.HTTPError, ValueError):
                    healthy = False
                return healthy, round((time.monotonic() - started) * 1000)
        results = await asyncio.gather(*(request(i) for i in range(30)))
    durations = sorted(row[1] for row in results)
    report = {'requests': 30, 'concurrency': 3, 'errors': sum(not row[0] for row in results),
        'p50_ms': statistics.median(durations), 'p95_ms': durations[math.ceil(len(durations) * .95)-1]}
    print(json.dumps(report))
    return report['errors'] == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8001')
    raise SystemExit(0 if asyncio.run(check(parser.parse_args().base_url)) else 1)
