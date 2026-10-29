"""Explicit offline Spark composition. No TTS calls, recordings or user questions."""
import argparse,asyncio,json
from sqlalchemy import select
from sqlalchemy.orm import Session
from ilma_api import settings
from ilma_api.db import engine,AppVoiceVariant,Institution
from ilma_api.main import get_institution_index
from ilma_api.voice_agent import Conversation
from ilma_api.human_turn import prepare,packet
from ilma_api.human_stream import generate
from ilma_api.human_variants import fingerprint,checked,store

async def compose(bank_ids=None):
    if engine.dialect.name!='mysql' or engine.url.database!='ilma':raise RuntimeError('Only the ilma MySQL database is permitted')
    AppVoiceVariant.__table__.create(engine,checkfirst=True)
    with Session(engine) as db:banks=get_institution_index(db)
    report=[]
    for bank in banks:
        if bank.get('coverage')!='full' or bank_ids and bank['id'] not in bank_ids:continue
        for language in ('bn','en'):
            for intent in ('bank_overview','bank_condition'):
                c=Conversation(institution_id=bank['id'],language=language,basis='islamic' if bank.get('islamic') else 'conventional')
                with Session(engine) as db:
                    prompt=('ব্যাংকটির বর্তমান অবস্থা কেমন?' if language=='bn' else 'What is the current condition of this bank?') if intent=='bank_condition' else ('ব্যাংকটি সম্পর্কে একটি ধারণা দিন।' if language=='bn' else 'Give a general introduction to this bank.')
                    r,c,_,_,registry,facts=prepare(db,prompt,c,banks,forced=intent)
                    payload,decode=packet(r,c,{},registry,facts,'offline')
                    key=fingerprint(payload,registry)
                    existing=db.scalars(select(AppVoiceVariant).where(AppVoiceVariant.fingerprint==key)).all()
                    previous=[row.protocol['lines'] for row in existing];ordinals={row.ordinal for row in existing}
                for ordinal in range(5):
                    if ordinal in ordinals:continue
                    accepted=False
                    for attempt in range(3):
                        draft=await generate({**payload,'offline_variant':ordinal,'previous_variants':previous,'composition_instruction':'Choose a different opening and clause order from previous variants. First answer must be 35–45 spoken words including the next question. Include status and a safety reason; include a material weakness when supplied. Only permitted token lines.'},[])
                        if not checked(draft,payload,decode,registry) or draft.lines in previous:continue
                        with Session(engine) as db:
                            store(db,key,ordinal,bank['id'],language,intent,draft,settings.MUSE_SPARK_MODEL);db.commit()
                        previous.append(draft.lines);accepted=True;break
                    report.append(dict(bank_id=bank['id'],language=language,intent=intent,ordinal=ordinal,accepted=accepted))
                    print(json.dumps(report[-1]),flush=True)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true');parser.add_argument('--bank-id',type=int,action='append');args=parser.parse_args()
    if not args.live:parser.error('--live is required: this makes paid offline Spark calls')
    result=asyncio.run(compose(args.bank_id))
    raise SystemExit(0 if all(row['accepted'] for row in result) else 1)
