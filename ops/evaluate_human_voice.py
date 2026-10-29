"""Explicit opt-in live paraphrase evaluation on an isolated local preview.
Never run against the public service. Contains no recordings or personal data.
"""
import argparse,json,sys,time
from pathlib import Path
from urllib.parse import urlparse
import httpx

def frames(response):
    response.raise_for_status()
    result=None
    for frame in response.text.split('\n\n'):
        if frame.startswith('event: error'):raise RuntimeError('Preview returned a voice error')
        if frame.startswith('event: result'):
            result=json.loads(frame.split('data: ',1)[1])
    if result is None:raise RuntimeError('No result frame')
    return result

def evaluate(base,cases,output):
    parsed=urlparse(base)
    if parsed.hostname not in {'localhost','127.0.0.1'} or parsed.port in {None,80,443,8001}:
        raise ValueError('Use an isolated local preview port, never the production service')
    results=[]
    with httpx.Client(base_url=base,timeout=40) as client:
        banks=client.get('/v1/institutions/index').json();by_slug={b['slug']:b for b in banks}
        current=by_slug['ebl']['id'];corrected=by_slug['primebank']['id']
        for intent,phrases in cases.items():
            if len(phrases)!=15:raise ValueError('Each intent requires 10 Bangla and 5 English phrases')
            for i,text in enumerate(phrases):
                language='bn' if i<10 else 'en'
                # Fresh server memory for each phrase avoids testing the 20-turn
                # cap/repetition instead of understanding. This setup is a pure UI action.
                setup=frames(client.post('/v1/ask',json={'choice':'listen','context':{'agent':True,'speak':False,'ui_lang':language,'conversation':{'institution_id':current,'language':language}}}))
                if not setup['conversation'].get('conversation_token'):raise RuntimeError('Contextual engine is not enabled on this preview')
                start=time.monotonic()
                result=frames(client.post('/v1/ask',json={'text':text,'context':{'agent':True,'speak':False,'ui_lang':language,'conversation':setup['conversation']}}))
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
                results.append(dict(intent=intent,case=i+1,actual=actual,bank_ok=bank_ok,checked=checked,passed=passed,ms=round((time.monotonic()-start)*1000)))
                print(intent,i+1,'pass' if passed else 'FAIL',flush=True)
    score=sum(r['passed'] for r in results)/len(results) if results else 0
    summary=dict(total=len(results),passed=sum(r['passed'] for r in results),accuracy=score,unintended_bank_changes=sum(not r['bank_ok'] for r in results),cases=results)
    output.write_text(json.dumps(summary,indent=2))
    return score>=.95 and not summary['unintended_bank_changes']

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--base-url',default='http://127.0.0.1:8018');parser.add_argument('--output',type=Path,default=Path('/tmp/ilma-human-evaluation.json'));args=parser.parse_args()
    if not args.live:parser.error('Use --live explicitly; this makes paid provider requests on the preview')
    cases=json.loads((Path(__file__).resolve().parents[1]/'tests/human_voice_cases.json').read_text())
    sys.exit(0 if evaluate(args.base_url,cases,args.output) else 1)
