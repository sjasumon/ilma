"""Load a reviewed bank-awards pack into new tables. Additive and idempotent.

Usage: python -m ilma_api.migrate_awards /private/path/ilma_awards_input_v7.2.zip
The pack stays outside the repository. Existing tables and rows are never changed;
a row whose key already exists is left as it is.
"""
import csv,hashlib,io,json,sys,zipfile
from datetime import date
from pathlib import Path
from ilma_api.db import Awarder,BankAward,BankAwardSource,Institution

PACK='awards_v7.2'
BANKS={'EBL':'ebl','BRACBANK':'bracbank','CITYBANK':'citybank','MTB':'mtb','NCCBANK':'nccbank','PRIMEBANK':'primebank',
 'DUTCHBANGL':'dutchbangl','BANKASIA':'bankasia','SBACBANK':'sbacbank','NBL':'nbl','ISLAMIBANK':'islamibank'}
# Review corrections for v7.2 (29 Oct 2026). The 12th ICSB award is for CG
# excellence 2024 (its page URL and title say 2024), not 2025.
CORRECTIONS={'awd_ebl_icsb_2025_1969':{'award_year':'2024'},'awd_islamibank_icmab_2021_8750':{'hide_in_app':'1'}}
# Awards added after the pack, from Sumon's ICSB screenshots and the IFC 2026 winners list.
MANUAL=Path(__file__).resolve().parents[2]/'seed/manual_awards.json'


def read(source):
    if str(source).endswith('.zip'):
        with zipfile.ZipFile(source) as pack:
            names=set(pack.namelist())
            return {name:list(csv.DictReader(io.TextIOWrapper(pack.open(name),encoding='utf-8'))) for name in ('awarders.csv','awards.csv','award_sources.csv') if name in names}
    return {name:list(csv.DictReader(open(f'{source}/{name}',encoding='utf-8'))) for name in ('awarders.csv','awards.csv','award_sources.csv')}


def day(value):
    return date.fromisoformat(value) if value else None


def with_manual(tables):
    rows=json.loads(MANUAL.read_text(encoding='utf-8'))
    return {**tables,'awards.csv':[*tables['awards.csv'],*rows],'award_sources.csv':[*tables['award_sources.csv'],*[{**row['source'],'award_id':row['award_id']} for row in rows]]}


def load(db,tables):
    slugs={i.slug:i.id for i in db.query(Institution).filter(Institution.slug.in_(BANKS.values())).all()}
    added={'awarder':0,'bank_award':0,'bank_award_source':0};skipped=[]
    for row in tables['awarders.csv']:
        if db.get(Awarder,row['awarder_id']):continue
        db.add(Awarder(awarder_id=row['awarder_id'],name=row['name'],name_bn=row['name_bn'],awarder_type=row['awarder_type'],country=row['country'],website=row['website'],
            paid_flag=row['paid_flag'],evidence_url=row['evidence_url'],evidence_quote=row['evidence_quote'],note=row['note'],source_pack=PACK));added['awarder']+=1
    db.flush()
    loaded=set()
    for row in tables['awards.csv']:
        row={**row,**CORRECTIONS.get(row['award_id'],{})}
        institution=slugs.get(BANKS.get(row['bank_code']))
        # A row whose bank or awarder is not in the pack's registers is not loaded.
        if institution is None or db.get(Awarder,row['awarder_id']) is None:skipped.append(row['award_id']);continue
        loaded.add(row['award_id'])
        existing=db.get(BankAward,row['award_id'])
        if existing:
            # A correction may hide a row that an earlier load already added.
            if row['hide_in_app']=='1':existing.hide_in_app=True
            continue
        db.add(BankAward(award_id=row['award_id'],institution_id=institution,awarder_id=row['awarder_id'],award_name_en=row['award_name_en'],award_name_bn=row['award_name_bn'],
            short_name_bn=row['short_name_bn'],category=row['category'],award_year=int(row['award_year']) if row['award_year'].strip() else None,announced_on=day(row['announced_on']),result=row['result'],
            medal=row['medal'],scope=row['scope'],confirmation=row['confirmation'],paid_flag=row['paid_flag'],hide_in_app=row['hide_in_app']=='1',source_pack=PACK));added['bank_award']+=1
    db.flush();seen=set()
    for row in tables['award_sources.csv']:
        if row['award_id'] not in loaded:continue
        # An exact repeated source row (v7.2 repeats one GIFA awarder row) is stored once.
        key=hashlib.sha256('\x1f'.join(row[k] for k in ('award_id','url','source_kind','outlet','published_on','quote','language')).encode()).hexdigest()
        if key in seen or db.query(BankAwardSource.id).filter_by(row_hash=key).first():continue
        seen.add(key)
        db.add(BankAwardSource(award_id=row['award_id'],row_hash=key,url=row['url'],source_kind=row['source_kind'],outlet=row['outlet'],published_on=day(row['published_on']),
            quote=row['quote'],language=row['language'],is_pr_copy=row['is_pr_copy']=='1'));added['bank_award_source']+=1
    db.flush()
    return added,skipped


def migrate(source):
    from ilma_api.db import engine,SessionLocal
    if engine.dialect.name!='mysql' or engine.url.database!='ilma':raise ValueError('Award migration requires the ilma MySQL database.')
    for model in (Awarder,BankAward,BankAwardSource):model.__table__.create(engine,checkfirst=True)
    with SessionLocal() as db:
        added,skipped=load(db,with_manual(read(source)));db.commit()
    print(f'Awards ready in ilma; added {added}; skipped (bank or awarder not registered) {skipped}. Existing tables unchanged.')


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python -m ilma_api.migrate_awards <pack.zip or directory>')
    try:migrate(sys.argv[1])
    except Exception as error:raise SystemExit(f'Award migration failed: {type(error).__name__}. Credentials were not printed.') from None
