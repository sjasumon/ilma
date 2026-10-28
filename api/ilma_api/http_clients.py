"""One keep-alive HTTP pool per application worker, closed with its lifespan."""
import httpx
_client=None
async def start():
    global _client
    if _client is None:_client=httpx.AsyncClient(timeout=httpx.Timeout(25,connect=5),limits=httpx.Limits(max_connections=16,max_keepalive_connections=8,keepalive_expiry=60),follow_redirects=False)
async def stop():
    global _client
    client,_client=_client,None
    if client is not None:await client.aclose()
def shared():return _client
