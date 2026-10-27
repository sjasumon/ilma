"""Normalize approved v6.2 inputs; no collector metadata or news bodies leave input."""
import csv
from datetime import date
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile

from ilma_api.export_seed import read, CONFIG

FILES = ('incidents', 'incident_sources', 'incident_status_history', 'weak_bank_figures', 'weak_bank_ratings')


def key(*parts):
    return hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:20]


def inputs(path):
    path = Path(path)
    if path.is_dir():
        return {name: read(path/(name+'.csv')) for name in FILES}
    with ZipFile(path) as archive:
        entries = {}
        if sum(item.file_size for item in archive.infolist()) > 2*1024*1024:
            raise ValueError('Incident archive is too large.')
        for item in archive.infolist():
            if item.is_dir(): continue
            if '..' in Path(item.filename).parts or item.filename.startswith('/'):
                raise ValueError('Unsafe archive path.')
            name = Path(item.filename).stem
            if name not in FILES or name in entries:
                raise ValueError('Unexpected/duplicate archive file.')
            entries[name] = list(csv.DictReader(io.StringIO(archive.read(item).decode('utf-8-sig'))))
        if set(entries) != set(FILES): raise ValueError('Missing incident input file.')
        return entries


def convert(path, output, checked_on):
    checked_on = date.fromisoformat(checked_on).isoformat()
    data = inputs(path)
    # Existing seed supplies bank IDs. The supplement adds only its two named banks.
    existing = {r['slug'].upper(): r for r in read(CONFIG/'institution.csv')}
    added = {r['code']: r for r in read(CONFIG/'incident_banks.csv')}
    ids = {code: int(r['id']) for code, r in {**existing, **added}.items()}
    bindings = {(r['bank_code'],r['scope']): r for r in read(CONFIG/'incident_bindings.csv')}
    result = {name: [] for name in ('institution','institution_alias','source','fact','rating','bank_incident','incident_source','incident_status_change')}
    notes = {'excluded_single_source': [], 'withheld_metrics': [], 'status_corrections': []}
    for code,r in added.items():
        result['institution'].append(dict(id=int(r['id']),slug=code.lower(),name_bn=r['name_bn'],name_en=r['name_en'],type='bank',
            islamic=r['islamic'],licensed=True,listed=True,coverage=r['coverage']))
        aliases = [code,r['name_en'].replace(' PLC',''),r['name_bn'].replace(' পিএলসি','')]
        aliases += ['ন্যাশনাল ব্যাংক','National Bank'] if code=='NBL' else ['ইসলামী ব্যাংক','ইসলামি ব্যাংক','Islami Bank','IBBL']
        for alias in dict.fromkeys(aliases):
            result['institution_alias'].append(dict(institution_id=ids[code],alias=alias,lang='bn' if any('\u0980'<=c<='\u09ff' for c in alias) else 'en',source='approved-v6.2'))
    def source(identifier,url,title,publisher,published=None,page=None):
        result['source'].append(dict(source_id=identifier,url=url,title=title[:255],publisher=publisher,published_at=published,
            page=page,checked_by='agent-v6.2',checked_on=checked_on))
    for row in data['weak_bank_figures']:
        if row['bank_code'] not in added: raise ValueError('Unexpected supplemental bank.')
        if row['year']!='2025':raise ValueError('v6.2 source bindings are for 2025 audited figures.')
        metric = {'CRAR':'crar','NPL_RATIO':'npl_ratio','PROFIT_AFTER_TAX':'net_profit'}.get(row['metric_name'])
        if not metric:
            notes['withheld_metrics'].append(dict(bank=row['bank_code'],metric=row['metric_name'],reason='Not an explicit supported ratio; no derived NPL is invented.'))
            continue
        ratio = metric!='net_profit'
        value = Decimal(row['ratio_pct'])/100 if ratio else Decimal(row['metric_value'])
        binding = bindings.get((row['bank_code'],'financial_'+metric),bindings[(row['bank_code'],'financial')])
        identifier = 'v62-fin-'+row['bank_code'].lower()+'-'+metric
        page = int(binding['page'] or row['page_no'])
        source(identifier,binding['url'],added[row['bank_code']]['name_en']+' · 2025 audited figures',binding['publisher'],page=page)
        quote = binding['quote_override'] or row['quote']
        if not binding['quote_override']:
            context = [row.get('column_header'),row.get('header_row'),row.get('raw_value')]
            quote += '\nSource context: '+' | '.join(value for value in context if value)
        result['fact'].append(dict(fact_id=identifier,institution_id=ids[row['bank_code']],metric=metric,value=value,
            unit='ratio' if ratio else 'bdt',period=row['year'],period_end=row['year']+'-12-31',source_id=identifier,
            quote=quote,basis=row['basis'],checked_by='agent-v6.2',checked_on=checked_on))
    for row in data['weak_bank_ratings']:
        if row['target_type'].casefold()!='entity' or row['is_current']!='1': continue
        binding = bindings[(row['bank_code'],'rating')]
        identifier = 'v62-rating-'+row['bank_code'].lower()
        source(identifier,binding['url'],added[row['bank_code']]['name_en']+' · '+row['rating_agency']+' entity rating',binding['publisher'])
        result['rating'].append(dict(fact_id=identifier,institution_id=ids[row['bank_code']],agency=row['rating_agency'],
            long_term=row['long_term_rating'],short_term=row['short_term_rating'],outlook=row['outlook'].lower(),
            rated_on=row['rating_date'],valid_to=row['valid_until'] or None,source_id=identifier,quote=row['quote'],checked_by='agent-v6.2',checked_on=checked_on))
    sources = {}
    for row in data['incident_sources']:
        sources.setdefault(row['incident_id'],[]).append(row)
    # The supplied quotations describe a probe / approval to file, not a filed
    # court case or accepted charge. Keep them reported, rather than upgrading.
    corrections = {'ISLAMIBANK_SCAM_2022':'reported','PRIMEBANK_EMBEZZLE_2014':'reported'}
    kept = {}
    source_ids = {}
    for row in data['incidents']:
        incident = row['incident_id']; rows = sources.get(incident,[])
        if row['bank_code'] not in ids: raise ValueError('Incident refers to unknown bank.')
        independent = {urlsplit(r['url']).hostname.removeprefix('www.') for r in rows}
        if row['status']=='single_source' or (row['official']!='1' and len(independent)<2):
            notes['excluded_single_source'].append(incident);continue
        identifier = 'v62-'+incident
        status = corrections.get(incident,row['status'])
        if status!=row['status']:notes['status_corrections'].append(dict(incident=incident,supplied=row['status'],published=status))
        result['bank_incident'].append(dict(incident_id=identifier,institution_id=ids[row['bank_code']],kind=row['type'],
            title_bn=row['title_bn'],title_en=row['title_en'],status=status,official=row['official'],status_effect=False,
            started_on=row['started_on'] or None,first_reported_on=row['first_reported_on'],last_update_on=row['last_update_on'],
            checked_by='agent-v6.2',checked_on=checked_on))
        kept[incident]=identifier
        for r in rows:
            sid='v62-src-'+key(incident,r['url'])
            if (incident,r['url']) in source_ids:raise ValueError('Duplicate incident source.')
            source_ids[(incident,r['url'])]=sid
            source(sid,r['url'],row['title_en'],r['outlet'],r['published_on'])
            result['incident_source'].append(dict(incident_id=identifier,source_id=sid,quote=r['quote'],language=r['language']))
    for row in data['incident_status_history']:
        if row['incident_id'] not in kept:continue
        status=corrections.get(row['incident_id'],row['status'])
        sid=source_ids.get((row['incident_id'],row['url']))
        if not sid:raise ValueError('Status update has no matching source.')
        result['incident_status_change'].append(dict(change_id='v62-change-'+key(row['incident_id'],row['changed_on'],row['url']),
            incident_id=kept[row['incident_id']],status=status,changed_on=row['changed_on'],source_id=sid,quote=row['quote']))
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    for name,rows in result.items():
        with (output/(name+'.csv')).open('w',newline='',encoding='utf-8') as file:
            if not rows:raise ValueError('Required supplemental output is empty: '+name)
            writer=csv.DictWriter(file,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    manifest=dict(release_id='incidents-v6.2-'+checked_on,checked_on=checked_on,version='v6.2',search_window=None,
        counts={name:len(rows) for name,rows in result.items()},expected_status={'nbl':'high','islamibank':'high'})
    (output/'release.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'review_notes.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
    return result
