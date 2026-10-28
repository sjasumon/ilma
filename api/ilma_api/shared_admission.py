"""Atomic provider budgets shared by workers in the existing ilma MySQL DB."""
import hashlib
import hmac
import math
import secrets
import time
from datetime import datetime,timedelta
from sqlalchemy import text
from sqlalchemy.dialects.mysql import insert
from ilma_api.db import engine,AppRateCounter
from ilma_api import settings

class SharedAdmission:
    shared=True
    def __init__(self,bind=None):
        self.engine=bind or engine
        if self.engine.dialect.name!='mysql' or self.engine.url.database!='ilma':raise ValueError('Shared admission requires the ilma MySQL database.')
    def enter(self,address):
        if not settings.VOICE_LOG_SALT_CONFIGURED:raise RuntimeError('Shared admission requires a stable private salt.')
        now=time.time();client=hmac.new(settings.VOICE_LOG_SALT.encode(),('admission:'+address).encode(),hashlib.sha256).hexdigest()[:16];minute=int(now//60);day=int(now//86400)
        counters=[(f'api:c:{minute}:{client}',settings.API_CLIENT_PER_MINUTE,(minute+1)*60),(f'api:m:{minute}',settings.API_GLOBAL_PER_MINUTE,(minute+1)*60),(f'api:d:{day}',settings.API_GLOBAL_PER_DAY,(day+1)*86400)]
        table=AppRateCounter.__table__;lease='api:active:'+secrets.token_hex(16)+':'+client
        with self.engine.connect() as connection:
            locked=False
            try:
                locked=connection.execute(text("SELECT GET_LOCK('ilma:provider:admission', 1)")).scalar()==1
                if not locked:raise RuntimeError('Shared admission lock unavailable')
                connection.execute(table.delete().where(table.c.expires_at<=datetime.utcnow()))
                rows=dict(connection.execute(table.select().with_only_columns(table.c.key,table.c.count).where(table.c.key.in_([k for k,_,_ in counters]))).all())
                for key,limit,expiry in counters:
                    if rows.get(key,0)>=limit:connection.commit();return None,max(1,math.ceil(expiry-now))
                active=connection.execute(table.select().with_only_columns(table.c.key).where(table.c.key.like('api:active:%'))).scalars().all()
                if len(active)>=settings.API_GLOBAL_CONCURRENCY or sum(k.endswith(':'+client) for k in active)>=settings.API_CLIENT_CONCURRENCY:
                    connection.commit();return None,2
                for key,_,expiry in counters:
                    statement=insert(table).values(key=key,count=1,expires_at=datetime.utcfromtimestamp(expiry))
                    connection.execute(statement.on_duplicate_key_update(count=table.c.count+1))
                connection.execute(table.insert().values(key=lease,count=1,expires_at=datetime.utcnow()+timedelta(seconds=180)))
                connection.commit();return lease,0
            finally:
                connection.rollback()
                if locked:
                    connection.execute(text("SELECT RELEASE_LOCK('ilma:provider:admission')"));connection.commit()
    def leave(self,key):
        if not key:return
        with self.engine.begin() as connection:connection.execute(AppRateCounter.__table__.delete().where(AppRateCounter.key==key))
