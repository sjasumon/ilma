"""Opt-in source-backed review. Use a local preview with paid providers disabled.
Paragraph review artifacts belong in /tmp, never committed as financial fixtures.
"""
import json,re,time
from pathlib import Path
import httpx
import argparse
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8018');p.add_argument('--output',type=Path,default=Path('/tmp/ilma-wording-review.json'));args=p.parse_args();base=args.base_url.rstrip('/')
rows=[]
with httpx.Client(timeout=30) as client:
 for attempt in range(40):
  try:
   response=client.get(base+'/v1/institutions?list=demo')
   if response.status_code==200:break
  except httpx.HTTPError:pass
  time.sleep(.25)
 banks=response.json();assert len(banks)==11
 def ask(text='',conversation=None,choice=None,language='bn'):
  started=time.monotonic();context={'agent':True,'speak':False,'ui_lang':language}
  if conversation:context['conversation']=conversation
  payload={'context':context,**({'choice':choice} if choice else {'text':text})}
  response=client.post(base+'/v1/ask',json=payload);assert response.status_code==200,response.status_code
  results=[json.loads(frame.split('data: ',1)[1]) for frame in response.text.split('\n\n') if frame.startswith('event: result')]
  assert results and results[0]['type']=='agent_turn',response.text[:500]
  result=results[0];assert result['speech']==result['text'] and result['speech_format']=='paragraph'
  assert not re.search(r'[:;()—]|\bPLC\b|পিএলসি|\b[HWP][1-9]\b',result['speech']),result['speech']
  assert set(result['speech_fact_ids'])<={f['fact_id'] for f in result['facts']}
  return result,round((time.monotonic()-started)*1000)
 first={}
 for language in ['bn','en']:
  for bank in banks:
   result,ms=ask(bank['name_'+language],language=language)
   assert ('কারণ' if language=='bn' else 'because') in result['speech'],(bank['slug'],result['speech'])
   assert result['speech'].endswith('?')
   first[(bank['slug'],language)]=result
   rows.append({'bank':bank['slug'],'language':language,'turn':'first','text_ms':ms,'speech':result['speech'],'speech_fact_ids':result['speech_fact_ids']})
 for language in ['bn','en']:
  result=first[('primebank',language)];seen=set(result['speech_fact_ids'])
  for choice in ['detail','figures','history','fdr']:
   result,ms=ask(conversation=result['conversation'],choice=choice,language=language)
   ids=set(result['speech_fact_ids']);assert not seen&ids,(choice,seen&ids);seen|=ids
   rows.append({'bank':'primebank','language':language,'turn':choice,'text_ms':ms,'speech':result['speech'],'speech_fact_ids':result['speech_fact_ids']})
  result,ms=ask('আমার টাকা ব্যাংক বন্ধ হলে কি পাবো?' if language=='bn' else 'deposit insurance',result['conversation'],language=language)
  assert result['conversation']['state']=='NEXT'
  rows.append({'bank':'primebank','language':language,'turn':'insurance','text_ms':ms,'speech':result['speech'],'speech_fact_ids':result['speech_fact_ids']})
 args.output.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 print('Reviewed',len(rows),'actual source-backed paragraphs across 11 banks and BN/EN; no provider or microphone call.')

 print('Text response range ms:',min(r['text_ms'] for r in rows),max(r['text_ms'] for r in rows))
