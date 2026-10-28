"""Pre-provider admission for the single-worker deployment; no device-ID trust.

Counters are process-local and reset on restart. Run one worker/replica until a
shared ingress limiter is deployed. All protected routes share the same budget.
"""
import asyncio
import hashlib
import math
import time
from threading import Lock

from starlette.responses import JSONResponse

from ilma_api import settings
from ilma_api.voice import MAX_UPLOAD_BYTES

PROTECTED = {'/v1/voice', '/v1/ask', '/v1/speech', '/v1/services/readout'}


class Admission:
    def __init__(self, clock=time.monotonic):
        self.clock, self.lock = clock, Lock()
        self.clients = {}
        self.minute = self.day = self.clock()
        self.minute_count = self.day_count = self.active = 0

    def enter(self, address):
        key = hashlib.sha256(address.encode()).hexdigest()
        with self.lock:
            now = self.clock()
            if now - self.minute >= 60:
                self.minute, self.minute_count = now, 0
            if now - self.day >= 86400:
                self.day, self.day_count = now, 0
            if key not in self.clients:
                self.clients = {k: v for k, v in self.clients.items() if v[2] or now - v[0] < 60}
                if len(self.clients) >= 4096:
                    return None, 60
                self.clients[key] = [now, 0, 0]
            row = self.clients[key]
            if now - row[0] >= 60:
                row[0], row[1] = now, 0
            if self.day_count >= settings.API_GLOBAL_PER_DAY:
                return None, max(1, math.ceil(86400 - (now - self.day)))
            if row[1] >= settings.API_CLIENT_PER_MINUTE or self.minute_count >= settings.API_GLOBAL_PER_MINUTE:
                return None, max(1, math.ceil(max(60 - (now - row[0]), 60 - (now - self.minute))))
            if row[2] >= settings.API_CLIENT_CONCURRENCY or self.active >= settings.API_GLOBAL_CONCURRENCY:
                return None, 2
            row[1] += 1
            row[2] += 1
            self.minute_count += 1
            self.day_count += 1
            self.active += 1
            return key, 0

    def leave(self, key):
        with self.lock:
            row = self.clients.get(key)
            if row is None:
                return
            row[2] = max(0, row[2] - 1)
            self.active = max(0, self.active - 1)


class ProviderAdmissionMiddleware:
    def __init__(self, app, admission=None):
        self.app = app
        self.admission = admission or Admission()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or scope['path'].rstrip('/') not in PROTECTED:
            return await self.app(scope, receive, send)

        async def reject(status, code, message, retry=None):
            headers = {'Cache-Control': 'no-store'}
            if retry is not None:
                headers['Retry-After'] = str(retry)
            await JSONResponse({'error': {'code': code, 'message_en': message,
                'message_bn': {'origin_denied': 'এই সাইট থেকে অনুরোধ অনুমোদিত নয়।',
                    'request_limited': 'অনুরোধের সীমা হয়েছে। একটু পরে চেষ্টা করুন।',
                    'upload_timeout': 'আপলোডে সময় বেশি লাগছে। আবার চেষ্টা করুন।',
                    'audio_too_large': 'অনুরোধটি খুব বড়।',
                    'invalid_request': 'অনুরোধটি সঠিক নয়।'}[code]}}, status_code=status, headers=headers)(scope, receive, send)

        headers = dict(scope.get('headers', []))
        origin = headers.get(b'origin', b'').decode('latin-1')
        if origin and origin not in settings.CORS_ORIGINS:
            return await reject(403, 'origin_denied', 'This origin is not allowed.')
        # Never use X-Ilma-Device or parse untrusted forwarded headers here.
        client = scope.get('client')
        key, retry = self.admission.enter(client[0] if client else 'unknown')
        if key is None:
            return await reject(429, 'request_limited', 'Service request limit reached. Try again shortly.', retry)
        body = bytearray()
        try:
            limit = MAX_UPLOAD_BYTES if scope['path'].rstrip('/') in {'/v1/voice', '/v1/ask'} else 16384
            try:
                length = int(headers.get(b'content-length', b'0'))
                if length < 0:
                    raise ValueError()
            except ValueError:
                return await reject(400, 'invalid_request', 'Invalid request length.')
            if length > limit:
                return await reject(413, 'audio_too_large', 'Upload is too large.')
            deadline = time.monotonic() + settings.API_UPLOAD_TIMEOUT_SECONDS
            while True:
                try:
                    chunk = await asyncio.wait_for(receive(), max(.001, deadline - time.monotonic()))
                except asyncio.TimeoutError:
                    return await reject(408, 'upload_timeout', 'Upload timed out. Try again.')
                if chunk['type'] == 'http.disconnect':
                    return
                if len(body) + len(chunk.get('body', b'')) > limit:
                    return await reject(413, 'audio_too_large', 'Upload is too large.')
                body.extend(chunk.get('body', b''))
                if not chunk.get('more_body', False):
                    break
            delivered = False

            async def buffered_receive():
                nonlocal delivered
                if delivered:
                    return await receive()
                delivered = True
                payload = bytes(body)
                body.clear()
                return {'type': 'http.request', 'body': payload, 'more_body': False}

            # Hold the slot until the final SSE/speech response or cancellation.
            await self.app(scope, buffered_receive, send)
        finally:
            body.clear()
            self.admission.leave(key)
