"""Validated transactional seed loading for supplied ILMA exports."""
from datetime import date, datetime
from decimal import Decimal
import json
import re
from pathlib import Path
from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, inspect, text, delete
from sqlalchemy.orm import Session
from ilma_api import db as models
from ilma_api.export_seed import read, quote_numbers

TABLES = {'institution': models.Institution, 'source': models.Source, 'fact': models.Fact,
    'rating': models.Rating, 'event': models.Event, 'event_source': models.EventSource,
    'service_offer': models.ServiceOffer, 'insurance_rule': models.InsuranceRule}


def prepare_schema(engine):
    if engine.dialect.name == 'mysql' and engine.url.database != 'ilma':
        raise ValueError('Export import is restricted to the ilma database.')
    models.Base.metadata.create_all(engine)
    if engine.dialect.name == 'mysql':
        schema = inspect(engine)
        with engine.begin() as connection:
            if 'basis' not in {c['name'] for c in schema.get_columns('fact')}:
                connection.execute(text("ALTER TABLE fact ADD COLUMN basis VARCHAR(32) NOT NULL DEFAULT 'unknown'"))
            if not next(c for c in schema.get_columns('source') if c['name'] == 'published_at')['nullable']:
                connection.execute(text('ALTER TABLE source MODIFY published_at DATE NULL'))
            if 'variant' not in {c['name'] for c in schema.get_columns('service_offer')}:
                connection.execute(text("ALTER TABLE service_offer ADD COLUMN variant VARCHAR(16) NOT NULL DEFAULT 'main'"))


def typed(model, row):
    result = {}
    for key, value in row.items():
        if key not in model.__table__.columns: raise ValueError('Unknown column: ' + key)
        column = model.__table__.columns[key]
        if value == '': result[key] = None if column.nullable else ''; continue
        kind = column.type
        if isinstance(kind, Boolean): value = value.lower() in ('true', '1')
        elif isinstance(kind, DateTime): value = datetime.fromisoformat(value)
        elif isinstance(kind, Date): value = date.fromisoformat(value)
        elif isinstance(kind, Integer): value = int(value)
        elif isinstance(kind, Numeric): value = Decimal(value)
        result[key] = value
    return result


def load(directory, engine):
    directory = Path(directory)
    data, errors = {}, []
    for name, model in TABLES.items():
        path = directory / (name + '.csv')
        if path.exists(): data[name] = [typed(model, row) for row in read(path)]
    ids = {row['id'] for row in data.get('institution', [])}
    sources = {row['source_id'] for row in data.get('source', [])}
    seen = set()
    for name, rows in data.items():
        for row in rows:
            key = row.get('fact_id', row.get('offer_id', row.get('id', row.get('source_id'))))
            def fail(message): errors.append(f'{name}/{key}: {message}')
            if name == 'institution' and 'demo' in row['name_en'].lower(): fail('sample bank is forbidden')
            if 'institution_id' in row and row['institution_id'] not in ids: fail('unknown institution')
            if name in ('source','fact','rating','service_offer'):
                for field in ('checked_by','checked_on'):
                    if not row.get(field): fail('missing ' + field)
            if name == 'source':
                for field in ('url','title','publisher'):
                    if not row.get(field): fail('missing ' + field)
            if name in ('fact','rating'):
                if row['source_id'] not in sources: fail('missing source')
                if not row.get('quote'): fail('missing quote')
            if name == 'insurance_rule' and row['source_id'] not in sources:fail('missing official insurance source')
            if name == 'fact':
                unique = (row['institution_id'],row['metric'],row['period'])
                if unique in seen: fail('duplicate institution/metric/period')
                seen.add(unique)
                if row['unit']=='ratio' and not 0 <= row['value'] <= 1: fail('ratio outside 0..1')
            if name == 'service_offer':
                for field in ('source_url','page','quote','doc_date'):
                    if not row.get(field): fail('missing ' + field)
                if row.get('value_num') is not None and row['value_num'] not in quote_numbers(row['quote']) and not (
                    row['value_num']==0 and row['value_text'].casefold()=='free' and re.search(r'\bfree\b',row['quote'],re.I)): fail('number absent from quote')
                if row.get('variant','main') not in {'main','variant','excluded'}: fail('invalid card variant')
                if row.get('value_num') is not None and row['value_num'] < 0: fail('negative service value')
    if errors: raise ValueError('\n'.join(errors))
    prepare_schema(engine)
    release = json.loads((directory / 'release.json').read_text())
    with Session(engine) as db:
        try:
            if 'service_offer' in data:
                current_ids={row['offer_id'] for row in data['service_offer']}
                db.execute(delete(models.ServiceOffer).where(models.ServiceOffer.institution_id.in_(ids),
                    models.ServiceOffer.offer_id.like('svc-%'),~models.ServiceOffer.offer_id.in_(current_ids)))
            for name, model in TABLES.items():
                for row in data.get(name, []):
                    # Keep a genuine manual review when the same source is reimported.
                    key = tuple(row[column.name] for column in model.__table__.primary_key.columns)
                    existing = db.get(model, key if len(key)>1 else key[0])
                    if name=='fact' and existing is None:
                        existing=db.query(models.Fact).filter_by(institution_id=row['institution_id'],metric=row['metric'],period=row['period']).first()
                        if existing:row['fact_id']=existing.fact_id
                    if existing and getattr(existing, 'checked_by', '').casefold() == 'sumon' and all(
                        getattr(existing,key)==value for key,value in row.items() if key not in {'checked_by','checked_on'}):
                        for field in ('checked_by','checked_on'): row[field] = getattr(existing,field)
                    db.merge(model(**row))
                db.flush()
            for row in read(directory / 'institution_alias.csv'):
                institution = int(row['institution_id'])
                if institution not in ids: raise ValueError('Alias references unknown institution')
                if not db.query(models.InstitutionAlias.id).filter_by(institution_id=institution,alias=row['alias']).first():
                    db.add(models.InstitutionAlias(institution_id=institution,alias=row['alias'],lang=row['lang'],source=row['source']))
                    db.flush()  # respect MySQL's case-insensitive collation
            from ilma_api.report_card import get_institution_report_card
            baseline = date.fromisoformat(release['export_date'])
            statuses = {row['slug']:get_institution_report_card(db,row['id'],baseline)['status']['code'] for row in data.get('institution',[])}
            if len(statuses)!=9 or any(status != ('no_data' if code=='sbacbank' else 'strong') for code,status in statuses.items()):
                raise ValueError('Demo status mismatch; thresholds unchanged, load rolled back: '+str(statuses))
            db.merge(models.Release(release_id=release['release_id'], note='Supplied v5.2 export; agent checked, manual checks pending'))
            db.commit()
        except Exception:
            db.rollback(); raise
    print('Imported:', {name:len(rows) for name,rows in data.items()}, 'release:',release['release_id'])
    print('Baseline statuses:',statuses)
    return statuses
