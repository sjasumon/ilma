"""Keep synchronous MySQL I/O off the event loop, with thread-owned sessions."""
import asyncio
import logging,time
from sqlalchemy.orm import Session

async def call(db,function):
    if not isinstance(db,Session) or db.get_bind().dialect.name!='mysql':return function(db)
    bind=db.get_bind()
    def run():
        with Session(bind=bind) as owned:
            started=time.monotonic()
            owned.connection()
            elapsed=round((time.monotonic()-started)*1000)
            if elapsed>=250:logging.getLogger(__name__).warning('database_connection_acquire_ms=%d',elapsed)
            result=function(owned)
            owned.commit()
            return result
    return await asyncio.to_thread(run)
