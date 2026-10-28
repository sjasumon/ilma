import asyncio
from unittest.mock import patch

from ilma_api import settings
from ilma_api.admission import Admission, ProviderAdmissionMiddleware


def test_budgets_share_routes_expire_and_release():
    now = [0]
    gate = Admission(lambda: now[0])
    with patch.object(settings, 'API_CLIENT_PER_MINUTE', 2), patch.object(settings, 'API_GLOBAL_PER_MINUTE', 3), patch.object(settings, 'API_GLOBAL_PER_DAY', 4):
        key, _ = gate.enter('a')
        second, _ = gate.enter('a')
        assert gate.enter('a')[0] is None
        gate.leave(key)
        gate.leave(second)
        other, _ = gate.enter('b')
        gate.leave(other)
        assert gate.enter('c')[0] is None  # global minute cap
        now[0] = 61
        key, _ = gate.enter('a')
        gate.leave(key)
        assert gate.enter('b')[1] > 60  # global daily budget
        now[0] = 86401
        key, _ = gate.enter('a')
        assert key
        gate.leave(key)


def test_concurrency_and_bounded_client_memory():
    gate = Admission(lambda: 0)
    with patch.object(settings, 'API_CLIENT_CONCURRENCY', 1), patch.object(settings, 'API_GLOBAL_CONCURRENCY', 2):
        a, _ = gate.enter('a')
        assert gate.enter('a') == (None, 2)
        b, _ = gate.enter('b')
        assert gate.enter('c') == (None, 2)
        gate.leave(a)
        c, _ = gate.enter('c')
        assert c
        gate.leave(b)
        gate.leave(c)
    gate.clients = {str(i): [0, 0, 0] for i in range(4096)}
    assert gate.enter('new') == (None, 60)


def test_http_rejections_happen_before_app_and_ignore_spoofed_device():
    async def run():
        called = []
        async def app(scope, receive, send):
            called.append((scope['path'], (await receive())['body']))
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'ok'})
        gate = Admission()
        middleware = ProviderAdmissionMiddleware(app, gate)
        async def request(path='/v1/voice', headers=(), messages=None, receive=None):
            pending = list(messages or [{'type': 'http.request', 'body': b'abc'}])
            async def normal_receive():
                return pending.pop(0)
            result = []
            async def send(message): result.append(message)
            await middleware({'type': 'http', 'method': 'POST', 'path': path,
                'headers': list(headers), 'client': ('client', 1)}, receive or normal_receive, send)
            assert gate.active == 0
            return result
        assert (await request(headers=[(b'origin', b'https://evil.example')]))[0]['status'] == 403
        assert not called
        assert (await request(headers=[(b'content-length', b'99999999')]))[0]['status'] == 413
        assert (await request(path='/v1/speech', messages=[{'type': 'http.request', 'body': b'x' * 16385}]))[0]['status'] == 413
        assert (await request(headers=[(b'content-length', b'invalid')]))[0]['status'] == 400
        async def slow_receive(): await asyncio.sleep(.1)
        with patch.object(settings, 'API_UPLOAD_TIMEOUT_SECONDS', .01):
            assert (await request(receive=slow_receive))[0]['status'] == 408
        gate = Admission()
        middleware.admission = gate
        with patch.object(settings, 'API_CLIENT_PER_MINUTE', 1):
            assert (await request(headers=[(b'x-ilma-device', b'first')]))[0]['status'] == 200
            response = await request('/v1/services/readout', [(b'x-ilma-device', b'changed')])
            assert response[0]['status'] == 429
            assert b'retry-after' in dict(response[0]['headers'])
        assert called == [('/v1/voice', b'abc')]
    asyncio.run(run())


def test_stream_slot_held_until_completion_and_cancellation():
    async def run():
        started, finish = asyncio.Event(), asyncio.Event()
        async def app(scope, receive, send):
            await receive()
            started.set()
            await finish.wait()
        gate = Admission()
        middleware = ProviderAdmissionMiddleware(app, gate)
        async def receive(): return {'type': 'http.request', 'body': b''}
        async def send(message): pass
        task = asyncio.create_task(middleware({'type': 'http', 'method': 'POST',
            'path': '/v1/voice', 'headers': [], 'client': ('a', 1)}, receive, send))
        await started.wait()
        assert gate.active == 1
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        assert gate.active == 0
    asyncio.run(run())


def test_leave_unknown_key_is_safe():
    gate = Admission(lambda: 0)
    gate.leave("missing-key")
    assert gate.active == 0
    key, _ = gate.enter("a")
    gate.leave(key)
    gate.leave(key)
    assert gate.active == 0
