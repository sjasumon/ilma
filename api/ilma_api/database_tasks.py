"""Keep synchronous MySQL I/O off the event loop, with thread-owned sessions."""
import asyncio
import logging,time
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

RETRYABLE={1205,1213}  # MySQL lock-wait timeout and deadlock: nothing was committed.

def retrying(work):
    """Run once more after MySQL gives up a transaction under simultaneous requests."""
    try:return work()
    except OperationalError as error:
        code=(getattr(error.orig,'args',None) or (None,))[0]
        if code not in RETRYABLE:raise
        logging.getLogger(__name__).warning('database_retry code=%s',code)
        return work()

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
    return await asyncio.to_thread(retrying,run)
