"""Do not gzip already-compressed streaming speech or buffer its first chunk."""
from starlette.middleware.gzip import GZipMiddleware
class StreamingSafeGZipMiddleware(GZipMiddleware):
    async def __call__(self,scope,receive,send):
        if scope.get('path','').startswith('/v1/audio/'):
            return await self.app(scope,receive,send)
        return await super().__call__(scope,receive,send)
