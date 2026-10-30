"""Offline, explicit service clip generation. Dry run never contacts a provider."""
import argparse,asyncio,hashlib,json,sys,os
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
# Planning uses an isolated SQLite copy of the published seed, never MySQL.
# Shared read-only view imports still require a syntactically valid DB config.
os.environ['DB_NAME']='ilma'
os.environ.setdefault('DB_USERNAME','offline-service-builder')
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from ilma_api.csv_loader import load
from ilma_api.bank_services import compare
from ilma_api.db import ServiceOffer
from ilma_api.service_clips import key,narration,selected_narration,ATTRIBUTES,manifest,DIRECTORY

def plan(db):
    choices=db.query(ServiceOffer.network,ServiceOffer.tier).filter_by(product_type='card',hidden=False).distinct().all();output=[]
    for network,tier in sorted(choices,key=lambda r:(r[0] or '',r[1] or '')):
        if not network or not tier:continue
        for attribute in ATTRIBUTES:
            result=compare(db,'card',network=network,tier=tier,compare_by=attribute)
            fresh=[b for b in result['rows'] if b.get('facts',{}).get(attribute) and not b['facts'][attribute]['stale']]
            if len(fresh)<2:continue
            text=selected_narration(result);clip_key=key(network,tier,attribute)
            output.append({'key':clip_key,'attribute':attribute,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'data_version':hashlib.sha256(json.dumps({k:v for k,v in result.items() if k!='readout'},default=str,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'file':'bn/'+clip_key.split(':',1)[1]+'.mp3'})
    return output

async def generate(items,directory,client,voice_id,api_key,model):
    directory=Path(directory);data=manifest(directory)
    for item in items:
        old=data['clips'].get(item['key'],{})
        if old.get('text_sha256')==item['text_sha256'] and old.get('voice_id')==voice_id and (directory/old.get('file','missing')).is_file():continue
        response=await client.post('https://api.elevenlabs.io/v1/text-to-speech/'+voice_id,headers={'xi-api-key':api_key},json={'text':item['text'],'model_id':model,'voice_settings':{'stability':.5,'similarity_boost':.75}},params={'output_format':'mp3_44100_128'},timeout=120)
        response.raise_for_status();audio=response.content
        if not audio:raise ValueError('Empty provider audio')
        path=directory/item['file'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(audio)
        data['clips'][item['key']]={**item,'voice_id':voice_id,'audio_sha256':hashlib.sha256(audio).hexdigest(),'reviewed':False,'reviewer':'','reviewed_at':''}
        directory.mkdir(parents=True,exist_ok=True);temp=directory/'manifest.tmp';temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.replace(directory/'manifest.json')
    return data

def publish_reviewed(items,source,destination=DIRECTORY):
    import shutil,re
    source=Path(source);destination=Path(destination);incoming=manifest(source);approved={}
    expected={item['key']:item['text_sha256'] for item in items}
    for clip_key,item in incoming['clips'].items():
        filename=item.get('file','')
        if not (item.get('reviewed') is True and item.get('reviewer') and item.get('reviewed_at') and re.fullmatch(r'bn/card-[a-z0-9-]+\.mp3',filename)):continue
        path=source/filename
        if item.get('text_sha256')!=expected.get(clip_key) or hashlib.sha256(item.get('text','').encode()).hexdigest()!=item['text_sha256']:continue
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item.get('audio_sha256'):continue
        target=destination/filename;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);approved[clip_key]=item
    if not approved:raise ValueError('No unchanged reviewed service audio is available to publish')
    destination.mkdir(parents=True,exist_ok=True);(destination/'manifest.json').write_text(json.dumps({'version':1,'clips':approved},ensure_ascii=False,indent=2)+'\n')
    return len(approved)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dry-run',action='store_true');parser.add_argument('--generate',action='store_true');parser.add_argument('--publish-reviewed',action='store_true');parser.add_argument('--env-file',type=Path);parser.add_argument('--key',action='append');parser.add_argument('--max-characters',type=int,default=750);parser.add_argument('--output',type=Path,default=Path('/tmp/ilma-service-audio-review'));parser.add_argument('--seed',type=Path,default=Path(__file__).resolve().parents[1]/'seed');parser.add_argument('--json-output',type=Path)
    args=parser.parse_args()
    if sum([args.dry_run,args.generate,args.publish_reviewed])!=1:parser.error('Select exactly one action: --dry-run, --generate or --publish-reviewed')
    engine=create_engine('sqlite://');load(args.seed,engine)
    with Session(engine) as db:items=plan(db)
    if args.key:
        selected=set(args.key)
        if selected-{item['key'] for item in items}:parser.error('Unknown clip key')
        items=[item for item in items if item['key'] in selected]
    for item in items:print(item['key'],len(item['text']),'characters\n'+item['text']+'\n')
    print('TOTAL:',len(items),'clips;',sum(len(i['text']) for i in items),'characters')
    if args.json_output:args.json_output.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
    if args.publish_reviewed:print('Published reviewed clips:',publish_reviewed(items,args.output))
    if args.generate:
        if args.env_file:
            from dotenv import load_dotenv
            load_dotenv(args.env_file,override=True)
        if not 500<=args.max_characters<=10000:parser.error('Invalid reviewed character limit')
        if any(not 500<=len(item['text'])<=args.max_characters for item in items):parser.error('Review narration lengths and explicitly set --max-characters before spending credits')
        from ilma_api import settings
        if args.env_file:
            import importlib
            importlib.reload(settings)
        import httpx
        if not settings.ELEVENLABS_API_KEY or not settings.ELEVENLABS_VOICE_ID:parser.error('Configured ElevenLabs credentials required')
        async def run():
            async with httpx.AsyncClient() as client:await generate(items,args.output,client,settings.ELEVENLABS_VOICE_ID,settings.ELEVENLABS_API_KEY,settings.ELEVENLABS_MODEL)
        asyncio.run(run())
