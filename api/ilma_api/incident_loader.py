"""Validate and transactionally load the curated incident supplement into ilma."""
import argparse
from datetime import date
from decimal import Decimal
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import delete
from sqlalchemy.orm import Session
from ilma_api import db as models
from ilma_api.csv_loader import typed, prepare_schema
from ilma_api.export_seed import read, quote_numbers
from ilma_api.bank_services import DEMO_CODES
from ilma_api.incidents import STATUS_LABELS,TYPE_LABELS

TABLES={'institution':models.Institution,'source':models.Source,'fact':models.Fact,'rating':models.Rating,
    'bank_incident':models.BankIncident,'incident_source':models.IncidentSource,'incident_status_change':models.IncidentStatusChange}
PRIMARY={'dsebd.org','dse.com.bd','cse.com.bd','nblbd.com','islamibankbd.com','bb.org.bd'}


def public_url(url):
    parsed=urlsplit(url)
    host=(parsed.hostname or '').removeprefix('www.')
    if parsed.scheme!='https' or not host or '.' not in host or parsed.username or parsed.password:
        raise ValueError('Incident sources require public HTTPS URLs without credentials.')
    try:
        import ipaddress
        ipaddress.ip_address(host)
    except ValueError: return host
    raise ValueError('IP addresses are not incident source domains.')


def merge_reviewed(db,model,row):
    identity=tuple(row[c.name] for c in model.__table__.primary_key.columns)
    old=db.get(model,identity if len(identity)>1 else identity[0])
    if old and getattr(old,'checked_by','').casefold()=='sumon' and all(
        getattr(old,k)==v for k,v in row.items() if k not in {'checked_by','checked_on'}):
        row={**row,'checked_by':old.checked_by,'checked_on':old.checked_on}
    db.merge(model(**row))


def load(directory,engine):
    if engine.dialect.name=='mysql' and engine.url.database!='ilma':raise ValueError('Incident import requires ilma.')
    directory=Path(directory);manifest=json.loads((directory/'release.json').read_text())
    if manifest['version']!='v6.2' or manifest.get('search_window') is not None:
        raise ValueError('Review the release version/search coverage before changing the import policy.')
    data={name:[typed(model,row) for row in read(directory/(name+'.csv'))] for name,model in TABLES.items()}
    ids={r['id'] for r in data['institution']}
    if {r['slug'] for r in data['institution']}!={'nbl','islamibank'} or len(ids)!=2:raise ValueError('Unexpected supplemental banks.')
    sources={r['source_id']:r for r in data['source']};incidents={r['incident_id']:r for r in data['bank_incident']}
    for name,rows in data.items():
        keys=[tuple(row[c.name] for c in TABLES[name].__table__.primary_key.columns) for row in rows]
        if len(keys)!=len(set(keys)):raise ValueError('Duplicate supplemental key: '+name)
        if len(rows)!=manifest['counts'][name]:raise ValueError('Manifest count differs: '+name)
    for source in sources.values():
        public_url(source['url'])
        if not source.get('checked_by') or not source.get('checked_on'):raise ValueError('Missing source provenance.')
    fact_keys=set()
    for row in data['fact']:
        if row['institution_id'] not in ids or row['source_id'] not in sources:raise ValueError('Invalid figure reference.')
        key=(row['institution_id'],row['metric'],row['period'])
        if key in fact_keys:raise ValueError('Duplicate supplemental figure.')
        fact_keys.add(key)
        if not row['value'].is_finite() or not row['quote']:raise ValueError('Invalid figure.')
        if row['metric']=='npl_ratio' and not 0<=row['value']<=1:raise ValueError('Invalid bad-loan ratio.')
        if row['metric'] not in {'crar','npl_ratio','net_profit'}:raise ValueError('Unsupported figure; no inferred ratios.')
        if row['metric'] in {'crar','npl_ratio'} and row['unit']!='ratio':raise ValueError('Ratio unit mismatch.')
        if row['metric']=='net_profit' and row['unit']!='bdt':raise ValueError('Profit unit mismatch.')
        quoted=quote_numbers(row['quote'])
        expected=abs(row['value'])*(100 if row['unit']=='ratio' else Decimal('0.0000001'))
        if expected not in quoted:raise ValueError('Figure absent from source quotation.')
        if row['basis'].endswith('_calculated'):
            # A calculated ratio must reproduce from inputs that are themselves quoted.
            match=re.search(r'Calculation: ([\d,]+\.\d+) ÷ ([\d,]+\.\d+) = (\d+\.\d+)%',row['quote'])
            if row['metric']!='npl_ratio' or not match:raise ValueError('Calculated figure lacks its calculation.')
            numerator,denominator=(Decimal(part.replace(',','')) for part in match.groups()[:2])
            if not {numerator,denominator}<=quote_numbers(row['quote'].split('\nCalculation:')[0]):raise ValueError('Calculation inputs are not quoted.')
            if (numerator/denominator).quantize(Decimal('0.0001'))!=row['value']:raise ValueError('Calculated figure does not reproduce.')
    for row in data['rating']:
        if row['institution_id'] not in ids or row['source_id'] not in sources or not row['quote']:raise ValueError('Invalid rating reference.')
    by_incident={};links=set()
    for row in data['incident_source']:
        if row['incident_id'] not in incidents or row['source_id'] not in sources or not row['quote']:raise ValueError('Invalid incident source.')
        by_incident.setdefault(row['incident_id'],[]).append(sources[row['source_id']])
        links.add((row['incident_id'],row['source_id']))
    for row in incidents.values():
        if row['kind'] not in TYPE_LABELS or row['status'] not in STATUS_LABELS or row['status_effect']:
            raise ValueError('Unsupported incident kind/status or unauthorized status effect.')
        if row['first_reported_on']>row['last_update_on'] or row['last_update_on']>date.fromisoformat(manifest['checked_on']):raise ValueError('Invalid incident dates.')
        linked=by_incident.get(row['incident_id'],[])
        hosts={public_url(r['url']) for r in linked}
        if row['official']:
            if not hosts or not hosts<=PRIMARY:raise ValueError('Primary-source flag lacks primary evidence.')
        elif len(hosts)<2:raise ValueError('Single-source incident cannot be published.')
    changes={}
    for row in data['incident_status_change']:
        if (row['incident_id'],row['source_id']) not in links or row['status'] not in STATUS_LABELS:raise ValueError('Unsourced status update.')
        incident=incidents[row['incident_id']]
        if not incident['first_reported_on']<=row['changed_on']<=incident['last_update_on']:raise ValueError('Invalid status date.')
        changes.setdefault(row['incident_id'],[]).append(row)
    for identifier,row in incidents.items():
        timeline=changes.get(identifier,[])
        if not timeline or max(timeline,key=lambda c:c['changed_on'])['status']!=row['status']:raise ValueError('Current status differs from sourced history.')
    aliases=read(directory/'institution_alias.csv')
    if len(aliases)!=manifest['counts']['institution_alias']:raise ValueError('Alias count differs.')
    if any(int(row['institution_id']) not in ids for row in aliases):raise ValueError('Unknown bank alias reference.')
    prepare_schema(engine)
    with Session(engine) as db:
        if not DEMO_CODES<={r.slug for r in db.query(models.Institution)}:raise ValueError('Load the original nine-bank seed first.')
        known={r.id for r in db.query(models.Institution)}|ids
        if any(row['institution_id'] not in known for row in incidents.values()):raise ValueError('Unknown incident bank.')
        try:
            for row in data['institution']:
                old=db.get(models.Institution,row['id'])
                conflict=db.query(models.Institution).filter_by(slug=row['slug']).first()
                if old and old.slug!=row['slug'] or conflict and conflict.id!=row['id']:raise ValueError('Bank ID collision; refusing overwrite.')
            # Replace only this managed supplement's links/history, not news or other data.
            managed=list(db.query(models.BankIncident).filter(models.BankIncident.incident_id.like('v62-%')))
            prior={row.incident_id:row for row in managed}
            for incoming in data['bank_incident']:
                old=prior.get(incoming['incident_id'])
                if old and old.checked_by.casefold()=='sumon' and all(getattr(old,k)==v for k,v in incoming.items() if k not in {'checked_by','checked_on'}):
                    incoming.update(checked_by=old.checked_by,checked_on=old.checked_on)
            for row in managed:db.delete(row)
            db.flush()
            for name,model in TABLES.items():
                for row in data[name]:merge_reviewed(db,model,row)
                db.flush()
            for row in aliases:
                identity=int(row['institution_id'])
                if not db.query(models.InstitutionAlias.id).filter_by(institution_id=identity,alias=row['alias']).first():
                    db.add(models.InstitutionAlias(institution_id=identity,alias=row['alias'],lang=row['lang'],source=row['source']));db.flush()
            from ilma_api.report_card import get_institution_report_card
            as_of=date.fromisoformat(manifest['checked_on'])
            statuses={r['slug']:get_institution_report_card(db,r['id'],as_of)['status']['code'] for r in data['institution']}
            if statuses!=manifest['expected_status']:raise ValueError('Unexpected supplemental status; transaction rolled back.')
            original={r.slug:get_institution_report_card(db,r.id,as_of)['status']['code'] for r in db.query(models.Institution).filter(models.Institution.slug.in_(DEMO_CODES))}
            from ilma_api.rules.status import demo_status
            if any(value!=demo_status(code) for code,value in original.items()):raise ValueError('Original bank baseline changed.')
            db.merge(models.Release(release_id=manifest['release_id'],note='Approved incident supplement; sourced financial flags; manual review pending.'))
            db.commit()
        except Exception:
            db.rollback();raise
    return {'statuses':statuses,'counts':{name:len(rows) for name,rows in data.items()}}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);args=parser.parse_args()
    from ilma_api.db import engine
    print(json.dumps(load(args.directory,engine)))
