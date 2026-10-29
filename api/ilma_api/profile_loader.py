"""Import individually quoted profile facts; absent evidence stays absent."""
import argparse,csv,re
from datetime import date
from decimal import Decimal
from pathlib import Path
from sqlalchemy.orm import Session
from ilma_api.db import BankProfile,Institution,engine

FIELDS={'founded_year','branches','sub_branches','atms','agent_outlets','customers','known_for'}

def validate(row):
    if row['field'] not in FIELDS:raise ValueError('Unknown profile field')
    if not row.get('quote') or not row.get('page') or not row.get('source_url','').startswith('https://'):
        raise ValueError('Profile requires a source URL, page and quotation')
    if not row.get('value'):raise ValueError('Empty profile fact')
    if row['field']!='known_for':
        values={Decimal(n.replace(',','')) for n in re.findall(r'\d[\d,]*(?:\.\d+)?',row['quote'])}
        amount=Decimal(row['value'].replace('+',''))
        if amount not in values and not ('mn' in row['quote'].lower() and amount/1000000 in values):
            raise ValueError('Profile value absent from quotation')
    return row

def load(path,bind=engine):
    if bind.dialect.name=='mysql' and bind.url.database!='ilma':raise ValueError('Use only the ilma database')
    rows=[validate(row) for row in csv.DictReader(Path(path).open(encoding='utf-8'))]
    BankProfile.__table__.create(bind,checkfirst=True)
    with Session(bind) as db:
        for row in rows:
            bank=db.query(Institution).filter_by(slug=row['bank_slug']).one_or_none()
            if bank is None:raise ValueError('Unknown profile bank')
            db.merge(BankProfile(fact_id=row['fact_id'],bank_id=bank.id,field=row['field'],value=row['value'],as_of=date.fromisoformat(row['as_of']),source_url=row['source_url'],page=row['page'],quote=row['quote'],checked_by='source-import',checked_on=date.today()))
        db.commit()
    return len(rows)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('csv');args=parser.parse_args()
    print('Sourced profile facts imported:',load(args.csv))
