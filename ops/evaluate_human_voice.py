"""Explicit opt-in live paraphrase evaluation on an isolated local preview.
Never run against the public service. Contains no recordings or personal data.
"""
import argparse,json,sys,time
from pathlib import Path
from urllib.parse import urlparse
import httpx
from concurrent.futures import ThreadPoolExecutor,as_completed

def frames(response):
    response.raise_for_status()
    result=None
    for frame in response.text.split('\n\n'):
        if frame.startswith('event: error'):raise RuntimeError('Preview returned a voice error')
        if frame.startswith('event: result'):
            result=json.loads(frame.split('data: ',1)[1])
    if result is None:raise RuntimeError('No result frame')
    return result

def request_turn(client,payload):
    # Concurrent setup and answer requests share the preview's admission budget.
    # Respect a bounded Retry-After rather than losing all completed cases.
    for attempt in range(3):
        started=time.monotonic();first_text=None;result=None;event_name='';data=[]
        with client.stream('POST','/v1/ask',json=payload) as response:
            status=response.status_code
            if status!=429:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith('event:'):event_name=line[6:].strip()
                    elif line.startswith('data:'):data.append(line[5:].strip())
                    elif not line and data:
                        value=json.loads('\n'.join(data));data=[]
                        if event_name=='error':raise RuntimeError('Preview returned a voice error')
                        if event_name in {'answer_sentence','result'} and value.get('text') and first_text is None:first_text=round((time.monotonic()-started)*1000)
                        if event_name=='result':result=value
                if result is None:raise RuntimeError('No result frame')
                result['_first_text_ms']=first_text;result['_complete_ms']=round((time.monotonic()-started)*1000)
                return result
            retry=response.headers.get('Retry-After','2')
        if attempt==2:raise RuntimeError('Preview admission remained limited')
        try:delay=float(retry)
        except ValueError:delay=2
        time.sleep(max(1,min(60,delay)))

def evaluate(base,cases,output,workers=2,sample=False):
    parsed=urlparse(base)
    if parsed.hostname not in {'localhost','127.0.0.1'} or parsed.port in {None,80,443,8001}:
        raise ValueError('Use an isolated local preview port, never the production service')
    results=[]
    with httpx.Client(base_url=base,timeout=40) as client:
        banks=client.get('/v1/institutions/index').json();by_slug={b['slug']:b for b in banks}
        current=by_slug['ebl']['id'];corrected=by_slug['primebank']['id']
        jobs=[]
        for intent,phrases in cases.items():
            if len(phrases)!=15:raise ValueError('Each intent requires 10 Bangla and 5 English phrases')
            jobs.extend((intent,i,text) for i,text in enumerate(phrases) if not sample or i in {0,1,10})
    def one(job):
        intent,i,text=job
        with httpx.Client(base_url=base,timeout=40) as client:
                language='bn' if i<10 else 'en'
                # Fresh server memory for each phrase avoids testing the 20-turn
                # cap/repetition instead of understanding. This setup is a pure UI action.
                setup=request_turn(client,{'choice':'bank_1','context':{'agent':True,'speak':False,'ui_lang':language,'conversation':{'institution_id':current,'compare_bank_ids':[current],'language':language}}})
                if not setup['conversation'].get('conversation_token'):raise RuntimeError('Contextual engine is not enabled on this preview')
                start=time.monotonic()
                result=request_turn(client,{'text':text,'context':{'agent':True,'speak':False,'ui_lang':language,'conversation':setup['conversation']}})
                steps=result.get('trace',{}).get('steps',[])
                provider=[s for s in steps if s.get('stage')=='PLAN' and s.get('reason','').startswith('http_')]
                if provider:raise RuntimeError('Live model access failed: '+provider[0]['reason']+'; evaluation stopped')
                expected='bank_overview' if intent=='correction' else intent
                bank=corrected if intent=='correction' else current
                actual=result.get('intent');bank_ok=result['conversation']['institution_id']==bank
                # Repeat is a server replay; every other free-text success needs
                # the generated reply to pass CHECK, not a template guess.
                checked=result.get('checked')=='code' or intent=='repeat'
                passed=actual==expected and bank_ok and checked
                return dict(intent=intent,case=i+1,actual=actual,bank_ok=bank_ok,checked=checked,passed=passed,ms=round((time.monotonic()-start)*1000),reply=result.get('text'),trace=steps)
    with ThreadPoolExecutor(max_workers=max(1,min(2,workers))) as pool:
        pending={pool.submit(one,job):job for job in jobs}
        for future in as_completed(pending):
            result=future.result();results.append(result)
            print(result['intent'],result['case'],'pass' if result['passed'] else 'FAIL',flush=True)
            output.write_text(json.dumps({'partial':True,'cases':results},ensure_ascii=False,indent=2));output.chmod(0o600)
    score=sum(r['passed'] for r in results)/len(results) if results else 0
    summary=dict(sample=sample,total=len(results),passed=sum(r['passed'] for r in results),accuracy=score,bank_target_failures=sum(not r['bank_ok'] for r in results),unintended_bank_changes=sum(not r['bank_ok'] and r['intent']!='correction' for r in results),cases=results)
    output.write_text(json.dumps(summary,ensure_ascii=False,indent=2));output.chmod(0o600)
    return score>=.95 and not summary['bank_target_failures']


def evaluate_v2(base,cases,output,workers=2,sample=False,auditor=None):
    import math,collections
    parsed=urlparse(base)
    if parsed.hostname not in {'localhost','127.0.0.1'} or parsed.port in {None,80,443,8001}:raise ValueError('Use an isolated local preview port')
    with httpx.Client(base_url=base,timeout=40) as client:
        client.get('/v1/health').raise_for_status()
        banks={b['slug']:b for b in client.get('/v1/institutions/index').json()}
    selected=[];groups=collections.Counter()
    for case in cases:
        group=case['id'].split('-')[0]
        if sample and groups[(group,case['language'])]>=1:continue
        selected.append(case);groups[(group,case['language'])]+=1
    results=[]
    def one(case):
        with httpx.Client(base_url=base,timeout=40) as client:
            bank=banks[case['current_bank']]['id'];expected=banks[case['expected_bank']]['id'];language=case['language']
            setup=request_turn(client,{'choice':'bank_1','context':{'agent':True,'speak':False,'ui_lang':language,'conversation':{'institution_id':bank,'compare_bank_ids':[bank],'language':language}}})
            if setup.get('protocol')!=2:raise RuntimeError('Token protocol is not active on the preview')
            start=time.monotonic();result=request_turn(client,{'text':case['text'],'context':{'agent':True,'speak':False,'ui_lang':language,'conversation':setup['conversation']}})
        trace=result.get('trace',{}).get('steps',[])
        provider=[s for s in trace if s.get('stage')=='PLAN' and s.get('reason','').startswith('http_')]
        if provider:raise RuntimeError('Provider access failed: '+provider[0]['reason'])
        conversation=result['conversation'];kinds={f['kind'] for f in result.get('facts',[])}
        intent_ok=result['intent']==case['expected_intent'];bank_ok=conversation['institution_id']==expected
        slots_ok=all(conversation.get(k)==v for k,v in case.get('slots',{}).items())
        facts_ok=not case.get('required_fact_kinds') or bool(set(case['required_fact_kinds'])&kinds)
        checked=result.get('checked')=='code' or case['expected_intent']=='repeat'
        protection=case['expected_intent']!='insurance' and bool(__import__('re').search(r'বন্ধ হলেও|সুরক্ষিত|ফেরত পাওয়ার|deposit protection|if the bank closes',result['speech'],__import__('re').I))
        calls=sum(t['stage']=='PLAN' and t['model']!='exact_option' for t in trace)
        passed=intent_ok and bank_ok and slots_ok and facts_ok and checked and not protection
        row=dict(id=case['id'],intent=case['id'].split('-')[0],language=language,actual=result['intent'],intent_ok=intent_ok,bank_ok=bank_ok,slots_ok=slots_ok,facts_ok=facts_ok,checked=checked,passed=passed,ms=result.get('_first_text_ms') or round((time.monotonic()-start)*1000),complete_ms=result.get('_complete_ms'),model_calls=calls,unsolicited_protection=protection,repairs=result.get('sentence_repairs',0),words=len(result.get('speech_tts','').split()),reply=result['text'],trace=trace)
        if auditor is not None:row['claim_audit']=auditor(case,setup,result)
        return row
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(one,case) for case in selected]
        for future in as_completed(futures):
            row=future.result();results.append(row);print(row['id'],'pass' if row['passed'] else 'FAIL',flush=True)
            output.write_text(json.dumps({'partial':True,'cases':results},ensure_ascii=False,indent=2));output.chmod(0o600)
    times=sorted(r['ms'] for r in results);total=len(results)
    rate=lambda predicate:sum(predicate(r) for r in results)/max(1,total)
    summary=dict(protocol=2,sample=sample,total=total,passed=sum(r['passed'] for r in results),accuracy=rate(lambda r:r['passed']),bank_target_failures=sum(not r['bank_ok'] for r in results),intent_accuracy=rate(lambda r:r['intent_ok']),slot_failures=sum(not r['slots_ok'] for r in results),required_fact_failures=sum(not r['facts_ok'] for r in results),unsolicited_protection=sum(r['unsolicited_protection'] for r in results),fallback_rate=rate(lambda r:not r['checked']),one_call_rate=rate(lambda r:r['model_calls']<=1),sentence_repair_rate=rate(lambda r:r['repairs']>0),p50_ms=times[len(times)//2] if times else None,p95_ms=times[math.ceil(len(times)*.95)-1] if times else None,cases=results)
    output.write_text(json.dumps(summary,ensure_ascii=False,indent=2));output.chmod(0o600)
    return summary['accuracy']>=.95 and not summary['bank_target_failures'] and not summary['unsolicited_protection']

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--sample',action='store_true');parser.add_argument('--legacy',action='store_true');parser.add_argument('--workers',type=int,default=1,choices=[1,2]);parser.add_argument('--base-url',default='http://127.0.0.1:8018');parser.add_argument('--output',type=Path,default=Path('/tmp/ilma-human-evaluation.json'));args=parser.parse_args()
    if not args.live:parser.error('Use --live explicitly; this makes paid provider requests on the preview')
    cases=json.loads((Path(__file__).resolve().parents[1]/('tests/human_voice_cases.json' if args.legacy else 'tests/human_voice_cases_v2.json')).read_text())
    sys.exit(0 if (evaluate if args.legacy else evaluate_v2)(args.base_url,cases,args.output,workers=args.workers,sample=args.sample) else 1)
