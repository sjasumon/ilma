"""Generate reviewed bilingual answers with exact, separately hashed spoken-number scripts."""
import argparse,asyncio,hashlib,json,os,re,sys
from pathlib import Path

def approved(path):
    data=json.loads(Path(path).read_text());rows=data['clips'];items=[]
    if data.get('approved') is not True:raise ValueError('Text review must be complete')
    expected={f'{lang}:q{n:03d}' for lang in ('bn','en') for n in range(1,94)}
    for row in rows:
        key=row['key'];text=row['text'];language=row['language']
        if key not in expected or language!=key.split(':')[0] or not isinstance(text,str) or not text.strip():raise ValueError('Invalid answer key, language or text')
        digest=hashlib.sha256(text.encode()).hexdigest()
        if digest!=row['text_sha256'] or len(text)!=row['chars']:raise ValueError('Reviewed text changed')
        file=language+'/'+key.split(':')[1]+'.mp3'
        if row['file']!=file:raise ValueError('Invalid recording path')
        items.append(dict(key=key,language=language,text=text,file=file,text_sha256=digest,approved_exact_text=True,review_sha256=data['review_sha256']))
    if len(items)!=186 or {i['key'] for i in items}!=expected:raise ValueError('All 93 answers in both languages are required')
    if sum(len(i['text']) for i in items)!=data['total_chars']:raise ValueError('Character total mismatch')
    return items

async def generate(items,directory,client):
    from build_approved_card_clips import generate as shared_generate
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    # One synthesis for identical same-language scripts, while retaining all question IDs.
    groups={}
    for row in items:groups.setdefault((row['language'],row['text_sha256']),[]).append(row)
    from ilma_api.exact_speech_numbers import prepare
    for row in items:
        speech,spans=prepare(row['text'],row['language'])
        if not spans:speech=row['text']
        row.update(tts_text=speech,tts_sha256=hashlib.sha256(speech.encode()).hexdigest(),tts_policy='exact-number-words-v1',numeric_spans=spans)
    canonical=[rows[0] for rows in groups.values()]
    manifest=await shared_generate(canonical,directory,client,request_timeout=120)
    for rows in groups.values():
        original=manifest['clips'][rows[0]['key']]
        for row in rows[1:]:
            dest=directory/row['file'];dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((directory/original['file']).read_bytes())
            manifest['clips'][row['key']]={**original,**row,'reused_from':original['key']}
    manifest.update(expected_clips=186,remaining_clips=0,batch_complete=True,unique_scripts=len(canonical))
    temp=directory/'manifest.tmp';temp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');temp.replace(directory/'manifest.json')
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--approved-json',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--env-file',type=Path);p.add_argument('--generate',action='store_true');a=p.parse_args();items=approved(a.approved_json)
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
    from ilma_api.exact_speech_numbers import prepare
    unique={(i['language'],i['text_sha256']):i for i in items}
    speech_chars=sum(len(prepare(i['text'],i['language'])[0]) for i in unique.values())
    print(f"186 mapped recordings; {len(unique)} unique scripts; {sum(len(i['text']) for i in items)} mapped characters; {speech_chars} spoken-script characters before reuse",flush=True)
    if not a.generate:return
    if a.env_file:
        from dotenv import load_dotenv
        load_dotenv(a.env_file,override=True)
        import importlib
        from ilma_api import settings
        importlib.reload(settings)
    os.environ['DB_NAME']='ilma'
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
    import httpx
    from ilma_api.elevenlabs import SpeechFailure
    async def run():
        async with httpx.AsyncClient(follow_redirects=False) as client:await generate(items,a.output,client)
    try:asyncio.run(run())
    except (ValueError,SpeechFailure) as error:print(str(error),file=sys.stderr);raise SystemExit(1)
if __name__=='__main__':main()
