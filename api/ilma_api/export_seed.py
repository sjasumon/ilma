"""CSV-only adapters for APP_SPEC_03/05. No scraper code or invented figures."""
import csv
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[2] / 'seed'


def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        return list(csv.DictReader(source))


def quote_numbers(quote):
    text = quote.translate(str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789'))
    text = re.sub(r'(?<=\d)\s*,\s*(?=\d)', '', text)
    return {Decimal(value) for value in re.findall(r'\d+(?:\.\d+)?', text)}


def classify(row):
    for mapping in read(CONFIG / 'product_type_map.csv'):
        if row['category'] == mapping['category'] and re.search(mapping['pattern'], row['product']):
            return mapping['product_type']
    raise ValueError('Unmapped service product: ' + row['product'])


def tenor(row):
    # Ambiguous multi-tenor products must never join a single-tenor comparison.
    text = row['product']
    if re.search(r'\d+\s*(?:&|and|[-–])\s*\d+\s*(?:Months|Years)', text, re.I): return None
    match = re.search(r'(\d+)\s*(?:\([^)]*\)\s*)?(Months?|Years?)', text, re.I)
    if not match:
        match = re.search(r'(\d+)\s*(?:\([^)]*\)\s*)?(Months?|Years?)', row['condition'], re.I)
    return int(match[1]) * (12 if match and match[2].lower().startswith('year') else 1) if match else None


def card_variants(rows):
    """Select a tier's printed retail header, then earliest source column."""
    def identity(row):
        return (row['bank_id'],row['network'],row['tier'],row['basis'],row['product'],row['column_header'])
    excluded={identity(row) for row in rows if row['category']=='card' and re.search(
        r'\b(corporate|defen[cs]e|army|payroll|rfcd|erq|fx|co.branded)\b|US\$',
        row['product']+' '+row['column_header']+' '+row['value'],re.I)}
    groups={}
    for row in rows:
        if row['category']!='card' or identity(row) in excluded:continue
        group=identity(row)[:4];card=identity(row)[4:]
        english=' '.join(re.findall(r"[A-Za-z]+",row['column_header'])).casefold()
        rank=(english!=row['tier'].casefold(),int(row.get('col_num') or 100000),card)
        current=groups.setdefault(group,{})
        current[card]=min(current.get(card,rank),rank)
    main={group:min(cards,key=cards.get) for group,cards in groups.items()}
    return {row['id']:('excluded' if identity(row) in excluded else 'main' if row['category']!='card' or
        identity(row)[4:]==main.get(identity(row)[:4]) else 'variant') for row in rows}


def bank_rows(directory, bank_codes=None):
    names = {row['code']: row for row in read(CONFIG / 'bank_names.csv')}
    if bank_codes is not None:
        if not bank_codes or not set(bank_codes) <= names.keys():
            raise ValueError('Unknown bank codes in converter test selection.')
        names = {code: row for code, row in names.items() if code in bank_codes}
    result = []
    for row in read(directory / 'banks.csv'):
        code = row['short_code'] or row['dse_code']
        if code not in names: continue
        result.append(dict(id=int(row['id']), slug=code.lower(), name_bn=names[code]['name_bn'],
            name_en=names[code]['name_en'], type='bank', islamic=False, licensed=True,
            listed=True, coverage='full'))
    if len(result) != len(names): raise ValueError('Export must contain exactly the configured demo banks (nine by default).')
    return result


def convert(directory, output, services=False, *, bank_codes=None, services_version=None):
    directory, output = Path(directory), Path(output)
    if services:
        version_match=re.search(r'v\d+\.\d+',directory.name)
        services_version=services_version or (version_match[0] if version_match else 'v5.4')
        if not re.fullmatch(r'v\d+\.\d+',services_version):raise ValueError('Invalid services release version.')
    output.mkdir(parents=True, exist_ok=True)
    # Tests explicitly select three banks; public CLI/runtime defaults stay nine.
    banks = bank_rows(directory, bank_codes)
    by_id = {str(row['id']): row for row in banks}
    exported = max(row['fetched_at'][:10] for row in read(directory / 'services.csv'))
    result = {}
    if services:
        hidden_rules = read(CONFIG / 'services_hidden.csv')
        offers, issues = [], []
        service_rows=read(directory / 'services.csv')
        variants=card_variants(service_rows)
        for row in service_rows:
            if row['bank_id'] not in by_id: continue
            for field in ['source_url', 'page', 'quote', 'doc_date', 'value']:
                if not row[field]: raise ValueError(f"Service {row['id']}: missing {field}")
            product_type = classify(row)
            reason = next((rule['reason'] for rule in hidden_rules if rule['bank'] == row['bank']
                and rule['category'] == row['category'] and rule['product_type'] in ('*', product_type)
                and rule['tier'] in ('*', row['tier'])), '')
            try: number = Decimal(row['value'].replace(',', ''))
            except InvalidOperation: number = None
            free=row['value'].casefold()=='free' and re.search(r'\bfree\b',row['quote'],re.I)
            if free:number=Decimal(0)
            if number is not None and not number.is_finite():raise ValueError('Non-finite service number')
            if number is not None and number not in quote_numbers(row['quote']) and not free:
                number = None
                # Preserve the original value but never use unsupported endpoints
                # in arithmetic/sorting or show unreadable/unproven numeric rows.
                if not re.search(r'\bfree\b', row['quote'], re.I):
                    reason = reason or 'numeric value is not printed in quote; requires verification'
                issues.append(dict(offer_id=row['id'], reason='numeric value not literal in quote'))
            if 'quote_unreadable' in row['condition']: reason = 'source quote unreadable; requires verification'
            doc_date = date.fromisoformat(row['doc_date'])
            stale = 'stale' in row['condition'].lower() or (date.fromisoformat(exported) - doc_date).days > 365
            offers.append(dict(offer_id='svc-' + row['id'], institution_id=int(row['bank_id']),
                category=row['category'], product=row['product'], product_type=product_type,
                network=row['network'] or None, tier=row['tier'] or None, tenor_months=tenor(row),
                attribute=row['attribute'], value_num=number, value_text=row['value'], unit=row['unit'],
                condition=row['condition'], basis=row['basis'], doc_date=row['doc_date'], stale=stale,
                source_url=row['source_url'], page=int(row['page']), quote=row['quote'],
                column_header=row['column_header'], variant=variants[row['id']], hidden=bool(reason), hidden_reason=reason,
                checked_by='agent-'+services_version, checked_on=exported))
        result['service_offer'] = offers
        (output / 'service_validation.json').write_text(json.dumps(issues, indent=2), encoding='utf-8')
    else:
        docs = {row['id']: row for row in read(directory / 'documents.csv')}
        sources, facts, ratings, events, links = [], [], [], [], []
        def source(key, doc_id, title, page=None, published=None, url=None, publisher=None):
            doc = docs[doc_id]
            sources.append(dict(source_id=key, url=url or doc['final_url'] or doc['url'], title=title[:255],
                publisher=publisher or doc['host'], published_at=published, page=page,
                checked_by='agent-v4', checked_on=exported))
            return key
        metrics = {'CRAR': ('crar', 'ratio'), 'NPL_RATIO': ('npl_ratio', 'ratio'), 'PROFIT_AFTER_TAX': ('net_profit', 'bdt')}
        for row in read(directory / 'annual_report_financials.csv'):
            if row['bank_id'] not in by_id or row['year'] not in ('2024', '2025') or row['is_rejected'] != '0' or row['metric_name'] not in metrics: continue
            metric, unit = metrics[row['metric_name']]
            key = 'export-fin-' + row['id']
            value = Decimal(row['metric_value']) / 100 if unit == 'ratio' else Decimal(row['metric_value']) * 1000000
            source(key, row['document_id'], by_id[row['bank_id']]['name_en'] + ' Annual Report ' + row['year'], int(row['page_no']))
            facts.append(dict(fact_id=key, institution_id=int(row['bank_id']), metric=metric, value=value,
                unit=unit, period=row['year'], period_end=row['year'] + '-12-31', source_id=key,
                quote=row['quote'], basis=row['basis'], checked_by='agent-v4', checked_on=exported))
        for row in read(directory / 'bank_credit_ratings.csv'):
            if row['bank_id'] not in by_id or row['is_current'] != '1' or row['target_type'].lower() != 'entity': continue
            key = 'export-rating-' + row['id']
            source(key, row['document_id'], by_id[row['bank_id']]['name_en'] + ' · ' + row['rating_agency'] + ' entity rating', int(row['page_no']) if row['page_no'] else None)
            ratings.append(dict(fact_id=key, institution_id=int(row['bank_id']), agency=row['rating_agency'],
                long_term=row['long_term_rating'], short_term=row['short_term_rating'], outlook=row['outlook'].lower() or None,
                rated_on=row['rating_date'], valid_to=row['valid_until'] or None, source_id=key,
                quote=row['quote'], checked_by='agent-v4', checked_on=exported))
        articles = {row['id']: row for row in read(directory / 'bank_news.csv')}
        for link in read(directory / 'article_banks.csv'):
            if link['bank_id'] not in by_id: continue
            row = articles[link['article_id']]
            key = f"export-news-{row['id']}-{link['bank_id']}"
            source(key, row['document_id'], row['title'], published=row['publish_date'], url=row['article_url'], publisher=row['source_newspaper'])
            events.append(dict(event_id=key, institution_id=int(link['bank_id']), type='other',
                title_bn=row['title'], title_en=row['title'], status='reported', official=False,
                event_date=row['publish_date'], last_update=row['publish_date'], checked_by='agent-v4', checked_on=exported))
            links.append(dict(event_id=key, source_id=key))
        aliases = []
        for row in read(directory / 'bank_aliases.csv'):
            if row['bank_id'] in by_id:
                aliases.append(dict(institution_id=int(row['bank_id']), alias=row['alias'],
                    lang='bn' if re.search('[\u0980-\u09ff]', row['alias']) else 'en', source='export-v5.2'))
        result = dict(institution=banks, institution_alias=aliases, source=sources, fact=facts,
                      rating=ratings, event=events, event_source=links)
    for name, rows in result.items():
        with (output / (name + '.csv')).open('w', encoding='utf-8', newline='') as destination:
            if rows:
                writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
                writer.writeheader(); writer.writerows(rows)
    if services:
        previous=json.loads((output/'release.json').read_text()) if (output/'release.json').exists() else {}
        manifest={**previous,'release_id':'services-'+services_version+'-'+exported,'export_date':exported,
            'services_version':services_version,'financial_version':previous.get('financial_version','v5.2')}
    else:manifest={'release_id':'export-v5.2-'+exported,'export_date':exported}
    (output / 'release.json').write_text(json.dumps(manifest), encoding='utf-8')
    print('Converted:', {name: len(rows) for name, rows in result.items()})
    return result
