"""Generate owner-reviewed deposit scripts exactly; no rewriting or pronunciation."""
import argparse,asyncio,hashlib,json,os,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'));sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_approved_card_clips import generate
from ilma_api.deposit_readout import PLANS,key

def plan(path,bindings):
    data=json.loads(Path(path).read_text());snapshot=json.loads(Path(bindings).read_text());clips=data['clips'];expected={key(*p) for p in PLANS};out=[]
    if len(clips)!=14 or sum(len(c['text']) for c in clips)!=data['total_chars']:raise ValueError('Approved deposit count/characters mismatch')
    for clip in clips:
        k=clip['key'];slug=k.removeprefix('deposit:bn:');text=clip['text']
        if not k.startswith('deposit:bn:') or slug not in expected:raise ValueError('Unknown deposit clip key')
        if len(text)!=clip['chars'] or hashlib.sha256(text.encode()).hexdigest()!=clip['text_sha256']:raise ValueError('Approved deposit text changed')
        file='bn/deposit_'+slug+'.mp3'
        if clip['file']!='static/audio/services/'+file:raise ValueError('Approved deposit filename changed')
        read=snapshot['readouts'][slug]
        if not re.fullmatch(r'[a-f0-9]{64}',read['source_sha256']):raise ValueError('Missing source binding')
        if not read['references'] or any(not r['offer']['source_url'].startswith('https://') for r in read['references']):raise ValueError('Narration reference source missing')
        for row in read['references']:
            if row['risk_code']!=('no_data' if row['bank_slug']=='sbacbank' else 'strong'):raise ValueError('Approved risk wording differs from current facts')
        out.append(dict(key=k,deposit_key=slug,text=text,file=file,text_sha256=clip['text_sha256'],source_sha256=read['source_sha256'],approved_exact_text=True,example_amount=read['example_amount'],example_months=read['example_months']))
    if {i['deposit_key'] for i in out}!=expected:raise ValueError('Missing or duplicate deposit clip')
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--approved-json',type=Path,required=True);p.add_argument('--bindings',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--env-file',type=Path);p.add_argument('--generate',action='store_true');a=p.parse_args();items=plan(a.approved_json,a.bindings)
    print('TOTAL:',len(items),'clips;',sum(len(i['text']) for i in items),'characters',flush=True)
    if a.generate:
        if a.env_file:
            from dotenv import load_dotenv
            load_dotenv(a.env_file,override=True)
            import importlib
            from ilma_api import settings
            importlib.reload(settings)
        os.environ['DB_NAME']='ilma'
        import httpx
        from ilma_api.elevenlabs import SpeechFailure
        async def run():
            async with httpx.AsyncClient(follow_redirects=False) as c:await generate(items,a.output,c,request_timeout=120)
        try:asyncio.run(run())
        except (ValueError,SpeechFailure) as e:print(str(e),file=sys.stderr);sys.exit(1)
