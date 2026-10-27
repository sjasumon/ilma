"""Local readiness probe. Nonzero exit activates the systemd failure signal."""
import json
import time
import httpx


def check(url='http://127.0.0.1:8001/v1/health'):
    started = time.monotonic()
    try:
        response = httpx.get(url, timeout=5, follow_redirects=False)
        body = response.json()
        healthy = response.status_code == 200 and body.get('ok') is True and body.get('db') == 'connected'
    except (httpx.HTTPError, ValueError, AttributeError):
        healthy = False
    return {'healthy': healthy, 'elapsed_ms': round((time.monotonic() - started) * 1000)}


if __name__ == '__main__':
    result = check()
    print(json.dumps(result))
    raise SystemExit(0 if result['healthy'] else 1)
