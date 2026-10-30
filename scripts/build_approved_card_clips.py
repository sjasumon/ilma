"""Generate explicitly approved card scripts verbatim; never rewrite speech text."""
import argparse,asyncio,hashlib,json,os,re,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))

def approved(path):
    data=json.loads(Path(path).read_text());items=[]
    for key,clip in data['clips'].items():
        if not re.fullmatch(r'bn:card-[a-z0-9-]+',key) or not isinstance(clip.get('text'),str) or not clip['text']:raise ValueError('Invalid approved clip')
        text=clip['text'];items.append({'key':key,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'file':'bn/'+key[3:]+'.mp3','approved_exact_text':True})
    if len(items)!=31 or sum(len(i['text']) for i in items)!=data['total_chars']:raise ValueError('Approved count/character total mismatch')
    return items
async def generate(items,directory,client):
    from ilma_api import elevenlabs
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    path=directory/'manifest.json'
    data=json.loads(path.read_text()) if path.exists() else {'version':1,'clips':{}}
    data.update(expected_clips=len(items),batch_complete=False)
    if len(elevenlabs.accounts())!=3:raise ValueError('Configure all three numbered key/voice pairs before generation')
    for item in items:
        old=data['clips'].get(item['key'],{});target=directory/item['file']
        if old.get('text_sha256')==item['text_sha256'] and target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==old.get('audio_sha256'):
            print(item['key'],'unchanged',flush=True);continue
        audio,used=await elevenlabs.synthesize(client,item['text'],voice_settings={'stability':.5,'similarity_boost':.75})
        target.parent.mkdir(exist_ok=True,parents=True);temp=target.with_suffix('.tmp');temp.write_bytes(audio);temp.replace(target)
        data['clips'][item['key']]={**item,**used,'audio_sha256':hashlib.sha256(audio).hexdigest(),'reviewed':True,'reviewer':'approved-text-and-file-integrity','reviewed_at':datetime.now(timezone.utc).isoformat(),'activation_authorized_by':'sjasumon','native_listening_reviewed':False}
        remaining=sum(i['key'] not in data['clips'] for i in items)
        data.update(remaining_clips=remaining,batch_complete=remaining==0)
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.replace(path)
        print(item['key'],used['key_name_used'],'saved',flush=True)
    return data
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--approved-json',type=Path,required=True);parser.add_argument('--env-file',type=Path);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--generate',action='store_true');args=parser.parse_args()
    items=approved(args.approved_json);print(len(items),'clips;',sum(len(i['text']) for i in items),'characters',flush=True)
    if args.generate:
        if args.env_file:
            from dotenv import load_dotenv
            load_dotenv(args.env_file,override=True)
        os.environ['DB_NAME']='ilma'
        import httpx
        from ilma_api.elevenlabs import SpeechFailure
        async def run():
            async with httpx.AsyncClient(follow_redirects=False) as client:await generate(items,args.output,client)
        try:asyncio.run(run())
        except (SpeechFailure,ValueError) as error:print(str(error),file=sys.stderr);sys.exit(1)
