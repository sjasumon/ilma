"""Build reviewed bank recordings verbatim from a hash-checked approved document."""
import argparse,asyncio,hashlib,json,os,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_approved_card_clips import generate
OMISSION='সুশাসনের জন্য দুই হাজার চব্বিশ সালে আইসিএসবি স্বর্ণপদকও পেয়েছে ব্যাংকটি। '
def normalized(name):return re.sub(r'[^a-z0-9]','',re.sub(r'^the\s+','',name.casefold()).replace('&','and'))
def plan(path,bindings):
    data=json.loads(Path(path).read_text());cards=json.loads(Path(bindings).read_text());clips=data['clips'];items=[]
    if len(clips)!=11 or sum(len(c['text']) for c in clips)!=data['total_chars']:raise ValueError('Approved bank count/character mismatch')
    for clip in clips:
        text=clip['text'];original=hashlib.sha256(text.encode()).hexdigest()
        if len(text)!=clip['chars'] or original!=clip['text_sha256']:raise ValueError('Approved bank text hash mismatch')
        name=normalized(clip['bank_name_en']);matches=[c for c in cards if normalized(c['institution']['name_en'])==name]
        if len(matches)!=1:raise ValueError('Bank name does not match exactly one database record')
        card=matches[0];slug=card['institution']['slug'];expected={'strong':'low','watch':'medium','high':'high','no_data':'no_data'}[card['status']['code']]
        if expected!=clip['risk_code']:raise ValueError('Approved risk differs from current sourced report')
        key=clip['key']
        if not re.fullmatch(r'bank:bn:[a-z0-9_]+',key):raise ValueError('Invalid approved bank key')
        file='bn/'+key.removeprefix('bank:bn:')+'.mp3'
        if clip['file']!='static/audio/bank/'+file:raise ValueError('Approved filename mismatch')
        omitted=False
        if slug=='bracbank' and not (card.get('award') and card['award']['awarder_confirmed']=='true' and str(card['award']['year'])=='2024'):
            if text.count(OMISSION)!=1:raise ValueError('Conditional BRAC sentence not found exactly once')
            text=text.replace(OMISSION,'',1);omitted=True
        if slug=='islamibank' and len(card['reasons'])!=2:raise ValueError('Islami report must retain two sourced reasons')
        if slug in {'primebank','dutchbangl','nccbank'}:
            group=card['comparison_facts'][0];rank=[r['bank_slug'] for r in group['rows']]
            expected_rank=1 if slug=='dutchbangl' else 0
            if len(rank)<2 or rank[expected_rank]!=slug:raise ValueError('Approved ranking no longer matches sourced comparison')
        items.append(dict(key=key,bank_slug=slug,file=file,text=text,text_sha256=hashlib.sha256(text.encode()).hexdigest(),source_sha256=card['readout']['source_sha256'],original_text_sha256=original,conditional_brac_award_omitted=omitted,approved_exact_text=True))
    if len({i['bank_slug'] for i in items})!=11:raise ValueError('Duplicate bank binding')
    return items
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--approved-json',type=Path,required=True);p.add_argument('--bindings',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--env-file',type=Path);p.add_argument('--generate',action='store_true');a=p.parse_args();items=plan(a.approved_json,a.bindings)
    print('TOTAL:',len(items),'clips;',sum(len(i['text']) for i in items),'characters',flush=True)
    for i in items:print(i['key'],len(i['text']),'characters;conditional award omitted:',i['conditional_brac_award_omitted'],flush=True)
    if a.generate:
        if a.env_file:
            from dotenv import load_dotenv
            load_dotenv(a.env_file,override=True)
        os.environ['DB_NAME']='ilma'
        import httpx
        from ilma_api.elevenlabs import SpeechFailure
        async def run():
            async with httpx.AsyncClient(follow_redirects=False) as client:await generate(items,a.output,client,request_timeout=120)
        try:asyncio.run(run())
        except (ValueError,SpeechFailure) as e:print(str(e),file=sys.stderr);sys.exit(1)
