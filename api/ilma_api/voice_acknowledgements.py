"""Cached-only acknowledgements: never synthesize on the waiting user's path."""
import asyncio,secrets
PHRASES={
 'bn':['আচ্ছা, দেখছি।','এক মুহূর্ত।','ঠিক আছে, বলছি।','দেখে বলছি।','আচ্ছা, একটু দেখি।','ঠিক আছে, দেখছি।'],
 'en':['Let me check.','One moment.','All right, let me see.','I will check that.','Let me take a look.','Okay, checking now.']}

async def cached(language,memory):
    from ilma_api.audio_cache import get_store
    store=get_store();candidates=[]
    for index,phrase in enumerate(PHRASES[language]):
        if index==memory.get('last_ack'):continue
        if await asyncio.to_thread(store.valid_cache,store.key(phrase,language,True),True):candidates.append((index,phrase))
    if not candidates:return None
    index,phrase=secrets.choice(candidates)
    ticket=await store.register([phrase],language,short=True)
    if ticket:memory['last_ack']=index
    return {**ticket,'role':'acknowledgement'} if ticket else None
