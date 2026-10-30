"""Generate text-approved frozen loan examples offline; no runtime provider calls."""
import argparse,asyncio,hashlib,json,os,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_approved_card_clips import generate

def plan(path):
    rows=json.loads(Path(path).read_text());items=[]
    if not isinstance(rows,list) or len(rows)!=4:raise ValueError('Review all four loan scripts together')
    for row in rows:
        kind=row['product_type'];slug=kind.replace('_','-');text=row['text'];source=row['source_sha256']
        if kind not in {'home_loan','auto_loan','personal_loan','loan_against_fdr'}:raise ValueError('Unknown loan type')
        if not re.fullmatch(r'[a-z0-9-]+',slug) or not re.fullmatch(r'[a-f0-9]{64}',source) or not text:raise ValueError('Invalid loan review entry')
        items.append(dict(key=kind,file='bn/'+slug+'.mp3',text=text,text_sha256=hashlib.sha256(text.encode()).hexdigest(),source_sha256=source,approved_exact_text=True))
    if len({i['key'] for i in items})!=4:raise ValueError('Duplicate loan script')
    return items
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--approved-json',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--env-file',type=Path);parser.add_argument('--generate',action='store_true');args=parser.parse_args()
    items=plan(args.approved_json)
    print('TOTAL:',len(items),'clips;',sum(len(i['text']) for i in items),'characters')
    for i in items:print(i['key'],len(i['text']),'characters\n'+i['text']+'\n')
    if args.generate:
        if args.env_file:
            from dotenv import load_dotenv
            load_dotenv(args.env_file,override=True)
        os.environ['DB_NAME']='ilma'
        import httpx
        from ilma_api.elevenlabs import SpeechFailure
        async def run():
            async with httpx.AsyncClient(follow_redirects=False) as c:await generate(items,args.output,c,request_timeout=120)
        try:asyncio.run(run())
        except (ValueError,SpeechFailure) as e:print(str(e),file=sys.stderr);sys.exit(1)
