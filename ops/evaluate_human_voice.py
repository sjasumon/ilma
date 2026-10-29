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
        response=client.post('/v1/ask',json=payload)
        if response.status_code!=429 or attempt==2:return frames(response)
        try:delay=float(response.headers.get('Retry-After','2'))
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

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--sample',action='store_true');parser.add_argument('--workers',type=int,default=1,choices=[1,2]);parser.add_argument('--base-url',default='http://127.0.0.1:8018');parser.add_argument('--output',type=Path,default=Path('/tmp/ilma-human-evaluation.json'));args=parser.parse_args()
    if not args.live:parser.error('Use --live explicitly; this makes paid provider requests on the preview')
    cases=json.loads((Path(__file__).resolve().parents[1]/'tests/human_voice_cases.json').read_text())
    sys.exit(0 if evaluate(args.base_url,cases,args.output,workers=args.workers,sample=args.sample) else 1)
