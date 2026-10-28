"""Owner-supplied extra publications, isolated from financial status rules."""
import argparse
import calendar
from functools import lru_cache
import csv
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from ilma_api.db import ExtraItem, RelatedEntity, Institution, Release, AppWatchItem
from ilma_api.export_seed import read, CONFIG
from ilma_api.csv_loader import prepare_schema, typed

KINDS={'announcement','report','press','rule','bank_notice','compliance'}

@lru_cache(maxsize=8192)
def normalize(value):
    return ' '.join(re.findall(r'\w+',value.casefold()))

def names_match(title, names):
    text=' '+normalize(title)+' '
    return any(' '+normalize(name)+' ' in text for name in names if normalize(name))

def circular_bank(title, banks, aliases):
    # Consider all 63 institutions, not just the app's eleven. Acronyms alone
    # are too broad; bank names / explicit multiword aliases must be present.
    text=' '+normalize(title)+' ';spans=[]
    for bank in banks:
        names=[bank['bank_name'],*aliases.get(bank['id'],[])]
        names += [re.sub(r'\b(?:plc|ltd|limited)\b[.]?','',name,flags=re.I).strip() for name in names]
        for name in {normalize(n) for n in names if len(normalize(n).split())>=2}:
            for match in re.finditer(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text):
                spans.append((match.start(),match.end(),bank['id']))
    # A nested short name (Trust Bank inside Mutual Trust Bank) is not a
    # second named bank. Separate spans such as BRAC and Pubali still reject.
    matches={bank for start,end,bank in spans if not any(
        other!=bank and a<=start and b>=end and b-a>end-start for a,b,other in spans)}
    if re.search(r'national bank of pakistan',title,re.I):return None
    return next(iter(matches)) if len(matches)==1 else None

def classify_announcement(row):
    text=row['title']+' '+row.get('body','')+' '+row.get('quote','')
    if row['topic']=='audit_emphasis':
        return 'audit_emphasis' if re.search(r'\b(?:qualified|adverse|disclaimer)\s+(?:opinion|of opinion)|going\s+concern',text,re.I) else 'financials'
    if row['topic']!='other':return row['topic']
    text=row['title']
    for topic,pattern in [('credit_rating',r'rating'),('dividend',r'dividend|record date'),('agm',r'annual general|\bagm\b|\begm\b'),
        ('board_meeting',r'board meeting|board of directors|board.*meeting'),('md_change',r'managing director|chief executive|\bceo\b'),
        ('financials',r'financial|earnings|\beps\b|\bnav\b|\bnocfps\b|profit'),('capital',r'capital|bond|share|securit|subscription')]:
        if re.search(pattern,text,re.I):return topic
    return 'company_notice'

def public_url(value, hosts=None):
    parsed=urlsplit(value)
    host=(parsed.hostname or '').removeprefix('www.')
    if parsed.scheme not in {'https','http'} or not host or parsed.username or parsed.password or (hosts and host not in hosts):
        raise ValueError('Invalid extra-data source URL')
    return value

def convert(directory, output, documents, checked_on):
    directory,output=Path(directory),Path(output);checked=date.fromisoformat(checked_on)
    cutoff=checked.replace(year=checked.year-1,day=min(checked.day,calendar.monthrange(checked.year-1,checked.month)[1]))
    ids={r['id'] for f in ('institution.csv','incidents/institution.csv') for r in read(CONFIG/f)}
    banks=read(directory/'banks.csv');codes={r['id']:(r['dse_code'] or r['short_code']) for r in banks};docs={r['id']:r for r in read(documents)}
    aliases={}
    for r in read(directory/'bank_aliases.csv'):aliases.setdefault(r['bank_id'],[]).append(r['alias'])
    output_rows=[];seen=set();notes={'unclassified_announcements':[],'dropped_report_year_mismatch':[], 'rejected_circular_links':[], 'missing_sources':[], 'duplicate_counts':{}, 'audit_retagging':[]}
    def add(key,bank,kind,topic,title,published,url,source_kind='document',year=None):
        if not url:notes['missing_sources'].append(key);return
        public_url(url,{'dsebd.org','dse.com.bd'} if kind=='announcement' else {'bb.org.bd'} if kind in {'press','rule','bank_notice','compliance'} else None)
        identity=(bank,kind,title,published,url)
        if identity in seen:
            notes['duplicate_counts'][kind]=notes['duplicate_counts'].get(kind,0)+1;return
        seen.add(identity)
        output_rows.append(dict(item_id='extra54-'+key,institution_id=bank,kind=kind,topic=topic,title=title,published_on=published,
            report_year=year,source_url=url,source_kind=source_kind,checked_by='agent-extra-v5.4',checked_on=checked_on))
    def doc_url(identifier):
        doc=docs.get(identifier,{})
        return doc.get('final_url') or doc.get('url') or ''
    for r in read(directory/'dse_bank_announcements.csv'):
        if r['bank_id'] not in ids:continue
        if r['trading_code']!=codes[r['bank_id']] or r['trading_code'].casefold() not in doc_url(r['document_id']).casefold():raise ValueError('DSE bank/code/source mismatch')
        if r['topic']=='audit_emphasis':notes['audit_retagging'].append(dict(id=r['id'],topic=classify_announcement(r)))
        add('dse-'+r['id'],r['bank_id'],'announcement',classify_announcement(r),r['title'],r['announcement_date'],doc_url(r['document_id']),'index')
    for r in read(directory/'bank_reports.csv'):
        if r['bank_id'] not in ids:continue
        if r['year_mismatch_flag']=='1':notes['dropped_report_year_mismatch'].append(r['id']);continue
        add('report-'+r['id'],r['bank_id'],'report',r['report_type'],r['report_title'],None,r['report_url'],year=r['title_year'] or r['year'])
    skips=[r['pattern'] for r in read(CONFIG/'press_release_skip.csv')]
    for r in read(directory/'bb_press_releases.csv'):
        title=re.sub(r'\s*more\.*\s*$','',r['title'],flags=re.I).strip()
        if r['is_market_operation']=='1' or any(re.search(pattern,title,re.I) for pattern in skips):continue
        if not re.search(r'fraud|crypto|mlm|unauthori[sz]ed|illegal lending|disrupt|deposit|interest|charges?|refinanc',title,re.I):continue
        add('press-'+r['id'],None,'press','bb_notice',title,r['release_date'],r['details_url'] or doc_url(r['document_id']), 'document' if r['details_url'] else 'index')
    circulars=read(directory/'bb_circulars.csv');corrected={}
    for r in circulars:
        bank=circular_bank(r['title'],banks,aliases);url=r['english_pdf_url'] or r['bangla_pdf_url']
        corrected[r['id']]=bank
        if bank in ids:add('notice-'+r['id'],bank,'bank_notice','bb_notice',r['title'],r['circular_date'],url)
        if re.match(r'^(?:BRPD|DOS|DFIM|PSD)(?:-|$)',r['department']) and cutoff<=date.fromisoformat(r['circular_date'])<=checked and re.search(r'deposit|interest|card|charges?|account|mobile|digital banking',r['title'],re.I):
            add('rule-'+r['id'],None,'rule','new_rule',r['title'],r['circular_date'],url)
    for r in read(directory/'bb_circular_banks.csv'):
        if r['bank_id'] in ids and corrected.get(r['circular_id'])!=r['bank_id']:notes['rejected_circular_links'].append(r)
    for r in read(directory/'bb_bank_actions.csv'):
        if r['bank_id'] not in ids:continue
        if r['action_type']!='special_exemption':raise ValueError('Unreviewed bank action type')
        add('action-'+r['id'],r['bank_id'],'compliance','other_compliance',r['quote'],r['action_date'],doc_url(r['document_id']))
    related=[dict(name=r['name'],parent_bank_id=r['parent_bank_id']) for r in read(directory/'related_entities.csv')]
    output.mkdir(parents=True,exist_ok=True)
    for name,rows in [('extra_item',output_rows),('related_entity',related)]:
        with (output/(name+'.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    manifest=dict(release_id='extra-v5.4-'+checked_on,checked_on=checked_on,counts={kind:sum(r['kind']==kind for r in output_rows) for kind in KINDS},related_entities=len(related))
    (output/'release.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'review_notes.json').write_text(json.dumps(notes,indent=2)+'\n')
    return manifest

def load(directory,engine):
    directory=Path(directory);manifest=json.loads((directory/'release.json').read_text())
    items=[typed(ExtraItem,r) for r in read(directory/'extra_item.csv')]
    entities=[typed(RelatedEntity,r) for r in read(directory/'related_entity.csv')]
    allowed={int(r['id']) for f in ('institution.csv','incidents/institution.csv') for r in read(CONFIG/f)}
    if len({r['item_id'] for r in items})!=len(items):raise ValueError('Duplicate extra-data key')
    for r in items:
        if r['kind'] not in KINDS or r['institution_id'] is not None and r['institution_id'] not in allowed:raise ValueError('Unapproved extra-data scope')
        if (r['kind'] in {'announcement','report','bank_notice','compliance'}) != (r['institution_id'] is not None):raise ValueError('Invalid bank association')
        if r['source_kind'] not in {'index','document'}:raise ValueError('Invalid source link kind')
        if r['kind']=='announcement' and r['topic']=='other':raise ValueError('Announcement needs explicit classification')
        if not r['item_id'].startswith('extra54-') or not r['title'] or not r['checked_by']:raise ValueError('Invalid extra data')
        public_url(r['source_url'],{'dsebd.org','dse.com.bd'} if r['kind']=='announcement' else {'bb.org.bd'} if r['kind'] in {'press','rule','bank_notice','compliance'} else None)
        if r['published_on'] and r['published_on']>date.fromisoformat(manifest['checked_on']):raise ValueError('Future publication')
    if {kind:sum(r['kind']==kind for r in items) for kind in KINDS}!=manifest['counts'] or len(entities)!=manifest['related_entities']:raise ValueError('Extra-data counts differ')
    prepare_schema(engine)
    with Session(engine) as db:
        if not allowed<={b.id for b in db.query(Institution)}:raise ValueError('Load bank and incident seeds first')
        prior={r.item_id:r for r in db.query(ExtraItem).filter(ExtraItem.item_id.like('extra54-%'))}
        for incoming in items:
            old=prior.get(incoming['item_id'])
            if old and old.checked_by.casefold()=='sumon' and all(getattr(old,key)==value for key,value in incoming.items() if key not in {'checked_by','checked_on'}):
                incoming.update(checked_by=old.checked_by,checked_on=old.checked_on)
        for old in prior.values():db.delete(old)
        db.flush()
        for r in items:db.merge(ExtraItem(**r))
        for r in entities:db.merge(RelatedEntity(**r))
        db.merge(Release(release_id=manifest['release_id'],note='Owner-supplied extra publications; no status effects; manual source review pending.'))
        db.commit()
    return manifest

def available(db):return inspect(db.connection()).has_table('extra_item')

def items(db,kind,bank=None):
    if not available(db):return []
    query=db.query(ExtraItem).filter_by(kind=kind)
    if bank is not None:query=query.filter_by(institution_id=bank)
    rows=query.order_by(ExtraItem.published_on.desc(),ExtraItem.report_year.desc(),ExtraItem.item_id).all()
    if kind=='report':
        def period(row):
            title=row.title.casefold()
            return 4 if 'annual' in title and 'half' not in title else 3 if re.search(r'third|3rd|q3|september',title) else 2 if re.search(r'half|second|2nd|q2|june',title) else 1
        rows.sort(key=lambda r:(r.report_year or 0,period(r),r.item_id),reverse=True)
    return rows

def view(row):
    banks={int(r['id']):r for f in ('institution.csv','incidents/institution.csv') for r in read(CONFIG/f)}
    bank=banks.get(row.institution_id,{})
    return dict(bank_name_bn=bank.get('name_bn'),bank_name_en=bank.get('name_en'),item_id=row.item_id,institution_id=row.institution_id,kind=row.kind,topic=row.topic,title=row.title,
        date=str(row.published_on) if row.published_on else None,year=row.report_year,source_url=row.source_url,source_kind=row.source_kind,
        affects_status=False,checked=row.checked_by.casefold()=='sumon')

def related_names(db):
    if not inspect(db.connection()).has_table('related_entity'):return []
    return db.query(RelatedEntity).all()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
    from ilma_api.db import engine
    print(json.dumps(load(args.directory,engine)))
