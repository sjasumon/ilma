"""Opt-in paid-provider timing check using fixed public bank names, not recordings."""
import argparse,asyncio,json,time,re,subprocess
from pathlib import Path
import httpx,imageio_ffmpeg
p=argparse.ArgumentParser();p.add_argument('--base-url',default='https://app.sumon.me');p.add_argument('--banks',type=int,choices=range(1,6),default=5);p.add_argument('--output',type=Path,default=Path('/tmp/ilma-voice-speed.json'));args=p.parse_args();base=args.base_url.rstrip('/')
def duration(data):
 result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-i','pipe:0','-progress','pipe:1','-f','null','-'],input=data,capture_output=True)
 values=re.findall(rb'out_time_us=(\d+)',result.stdout);return round(int(values[-1])/1000) if values else None
async def main():
 rows=[];pages=[]
 async with httpx.AsyncClient(timeout=100) as client:
  banks=(await client.get(base+'/v1/institutions/index')).json()
  async def heartbeat(done):
   while not done.is_set():
    start=time.monotonic()
    try:r=await client.get(base+'/',timeout=5);pages.append({'ms':round((time.monotonic()-start)*1000),'status':r.status_code})
    except httpx.HTTPError:pages.append({'ms':5000,'status':'timeout'})
    try:await asyncio.wait_for(done.wait(),.4)
    except asyncio.TimeoutError:pass
  async def download_audio(speech,row,started):
   urls=speech.get('audio_urls') or [speech['audio_url']];total=0;hits=[]
   for url in urls:
    data=bytearray()
    async with client.stream('GET',base+url,timeout=60) as audio:
     if audio.status_code!=200:raise RuntimeError('audio HTTP '+str(audio.status_code))
     hits.append(audio.headers.get('x-ilma-cache','unknown'))
     async for chunk in audio.aiter_bytes():
      if chunk and 'first_audio_ms' not in row:row['first_audio_ms']=round((time.monotonic()-started)*1000)
      data.extend(chunk)
    measured=await asyncio.to_thread(duration,bytes(data));total+=measured or 0
   row['audio_ms']=total;row['cache']=hits
  for slug in ['bracbank','primebank','ebl','mtb','bankasia'][:args.banks]:
   bank=next(b for b in banks if b['slug']==slug);conversation=None
   for label,text in [('first',bank['name_bn']),('detail','আরও বিস্তারিত')]:
    started=time.monotonic();row={'bank':slug,'turn':label,'input':'typed_fixed_bank','progress':[]};done=asyncio.Event();beat=asyncio.create_task(heartbeat(done));result=None;speech=None;name=None;audio_task=None
    context={'agent':True,'ui_lang':'bn','speak':True}
    if conversation:context['conversation']=conversation
    async with client.stream('POST',base+'/v1/ask',json={'text':text,'context':context},headers={'X-ILMA-Device':'speed-benchmark-fixed-public-banks-20261028'}) as response:
     if response.status_code!=200:raise RuntimeError('benchmark HTTP '+str(response.status_code))
     async for line in response.aiter_lines():
      if line.startswith('event: '):name=line[7:]
      if not line.startswith('data: '):continue
      data=json.loads(line[6:]);elapsed=round((time.monotonic()-started)*1000)
      if name=='progress':row['progress'].append(data)
      elif name=='result':result=data;row['text_ms']=elapsed
      elif name=='speech':speech=data;row['speech_event_ms']=elapsed;audio_task=asyncio.create_task(download_audio(data,row,started))
      elif name=='error':raise RuntimeError('benchmark error '+data.get('code','unknown'))
    if not result:raise RuntimeError('No result')
    conversation=result.get('conversation')
    if result.get('speech'):
     row['first_audio_ms']=row['text_ms'];row['audio_ms']=result.get('trace',{}).get('audio',{}).get('duration_ms')
    elif audio_task:await audio_task
    row['checked']=result.get('checked');row['steps']=result.get('trace',{}).get('steps',[])
    row['total_ms']=round((time.monotonic()-started)*1000);done.set();await beat
    rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ('progress','steps')},ensure_ascii=False),flush=True)
 report={'input':'typed fixed public bank names; first audio bytes, not device playback','rows':rows,'page_loads':pages,'page_max_ms':max((x['ms'] for x in pages),default=None),'page_errors':sum(x['status']!=200 for x in pages)}
 args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2));print('page_max_ms',report['page_max_ms'],'page_errors',report['page_errors'],flush=True)
asyncio.run(main())
