"""Keep synchronous MySQL I/O off the event loop, with thread-owned sessions."""
import asyncio
from sqlalchemy.orm import Session

async def call(db,function):
    if not isinstance(db,Session) or db.get_bind().dialect.name!='mysql':return function(db)
    bind=db.get_bind()
    def run():
        with Session(bind=bind) as owned:
            result=function(owned)
            owned.commit()
            return result
    return await asyncio.to_thread(run)
