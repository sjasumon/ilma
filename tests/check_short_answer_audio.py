"""Opt-in real TTS duration gate for a private source-backed review artifact.
Run on the deployment host with private configuration. Can incur TTS costs.
No recording, transcript, source export or generated MP3 is published.
"""
import argparse,asyncio,json
from pathlib import Path
import httpx
from ilma_api import settings
from ilma_api.answer_wording import validate_spoken_answer
from ilma_api.audio_cache import AudioStore
p=argparse.ArgumentParser();p.add_argument('--review',type=Path,default=Path('/tmp/ilma-wording-review.json'));p.add_argument('--output',type=Path,default=Path('/tmp/ilma-short-audio-metrics.json'));args=p.parse_args()
async def main():
 rows=json.loads(args.review.read_text());results=[];gate=asyncio.Semaphore(2)
 async with httpx.AsyncClient() as client:
  store=AudioStore(client=client)
  async def one(row):
   async with gate:
    validate_spoken_answer(row['speech'],row['language'],first=row['turn']=='first')
    ticket=await store.register([row['speech']],row['language'],short=True)
    assert ticket and len(ticket['audio_urls'])==1
    assert await store.wait(ticket),'Speech generation failed'
    item=store.ticket(ticket['audio_url'].rsplit('/',1)[-1][:-4]);meta=store.directory/(item['key']+'.json')
    for _ in range(100):
     if meta.exists():break
     await asyncio.sleep(.05)
    measured=json.loads(meta.read_text())['duration_ms'];assert measured is not None
    result={'bank':row['bank'],'language':row['language'],'turn':row['turn'],'duration_ms':measured,'clips':1,'words':len(row['speech'].split())}
    results.append(result);print(json.dumps(result),flush=True)
  try:await asyncio.gather(*(one(row) for row in rows))
  finally:await store.close()
 args.output.write_text(json.dumps({'speed':settings.TTS_SPEED,'results':results},indent=2))
 for row in results:
  validate_spoken_answer('',row['language'],duration_ms=row['duration_ms'])
  if row['turn']=='first':assert 12000<=row['duration_ms']<=22000,('Introduction target miss',row)
 print('All',len(results),'paragraphs meet the word, introduction 12–22-second and ordinary 30-second gates; configured speed',settings.TTS_SPEED)
asyncio.run(main())
