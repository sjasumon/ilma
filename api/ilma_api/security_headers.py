"""Response headers without buffering or disrupting streamed voice answers."""
import base64
import hashlib
import re

HEADERS = {
    b'strict-transport-security': b'max-age=31536000',
    b'x-content-type-options': b'nosniff',
    b'referrer-policy': b'strict-origin-when-cross-origin',
    b'content-security-policy': (
        b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        b"font-src 'self'; img-src 'self' data:; media-src 'self' data: blob:; "
        b"connect-src 'self'; worker-src 'self'; object-src 'none'; "
        b"base-uri 'none'; form-action 'self'; frame-ancestors 'none'"),
}


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        documentation=scope.get('path') in {'/docs','/redoc','/docs/oauth2-redirect'}
        start=None
        chunks=[]
        async def secured_send(message):
            nonlocal start
            # Only generated API documentation needs its CDN and initializer.
            # Hash those exact inline bytes; keep the app and SSE policy strict.
            if documentation and message['type']=='http.response.start':
                start=message
                return
            if documentation and message['type']=='http.response.body':
                chunks.append(message.get('body',b''))
                if message.get('more_body',False):
                    return
                body=b''.join(chunks)
                hashes=[b"'sha256-"+base64.b64encode(hashlib.sha256(code).digest())+b"'"
                    for code in re.findall(rb'<script(?:\s[^>]*)?>(.*?)</script>',body,re.S) if code.strip()]
                policy=HEADERS[b'content-security-policy'].replace(b"script-src 'self'",b"script-src 'self' https://cdn.jsdelivr.net "+b' '.join(hashes))
                policy=policy.replace(b"style-src 'self' 'unsafe-inline'",b"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com").replace(b"font-src 'self'",b"font-src 'self' https://fonts.gstatic.com").replace(b"img-src 'self' data:",b"img-src 'self' data: https://fastapi.tiangolo.com")
                headers=list(start.get('headers',[]))+[(key,policy if key==b'content-security-policy' else value) for key,value in HEADERS.items()]+[(b'cache-control',b'no-store, no-transform')]
                await send({**start,'headers':headers})
                await send({'type':'http.response.body','body':body})
                return
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                present = {key.lower() for key, _ in headers}
                headers.extend((key, value) for key, value in HEADERS.items() if key not in present)
                message = {**message, 'headers': headers}
            await send(message)
        await self.app(scope, receive, secured_send if scope['type'] == 'http' else send)
