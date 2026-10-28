"""Populate public demo speech in the background; never delays application start."""
import asyncio
import os
from ilma_api import settings
from ilma_api.audio_cache import get_store

def demo_phrases():
    from sqlalchemy.orm import Session
    from ilma_api.db import engine
    from ilma_api.bank_services import demo_banks
    from ilma_api.voice_agent import bank_summary,insurance
    from ilma_api.short_speech import parts,QUESTIONS
    if engine.dialect.name!='mysql' or engine.url.database!='ilma':return []
    phrases=[]
    with Session(engine) as db:
        for lang,index in [('bn',0),('en',1)]:
            for bank in demo_banks(db,include_incident_banks=True):
                lines=parts(db,bank_summary(db,bank.id),{'state':'BANK','institution_id':bank.id,'language':lang},QUESTIONS['BANK'][index],'bank_summary')
                phrases.extend((line,lang) for line in lines)
            phrases.extend((question[index],lang) for question in QUESTIONS.values())
            from ilma_api.voice_assets import CATALOG
            phrases.extend((pair[index],lang) for key,pair in CATALOG.items() if key.startswith('ivr_') and key!='ivr_confirm')
            phrases.extend((line,lang) for line in parts(db,insurance(db,None),{'state':'NEXT','institution_id':None,'language':lang},QUESTIONS['NEXT'][index],'insurance'))
    return list(dict.fromkeys(phrases))

async def warm():
    if not settings.TTS_PREWARM or not settings.ELEVENLABS_API_KEY:return
    store=get_store();await asyncio.to_thread(store.folders)
    lock=await asyncio.to_thread(store.lock,'warmup')
    if lock is None:return
    try:
        for text,language in await asyncio.to_thread(demo_phrases):
            key=store.key(text,language)
            if await asyncio.to_thread((store.directory/(key+'.mp3')).is_file):continue
            job=await store.job(key,text,language)
            await job.done.wait()
            await asyncio.sleep(.05)
    finally:os.close(lock)

async def maintain():
    if not settings.ELEVENLABS_API_KEY:return
    store=get_store()
    while True:
        try:
            await asyncio.to_thread(store.folders)
            await asyncio.to_thread(store.sweep)
        except OSError:pass
        await asyncio.sleep(60)
