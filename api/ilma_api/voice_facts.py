"""Fixed database retrieval for detail/glossary answers. Never synthesizes figures."""
import re
from ilma_api.db import Fact, Rating, Event, AppContent
from ilma_api.voice_text import normalize_alias

TOPICS = [
    ('npl_ratio', r'\bnpl\b|খেলাপি|bad loan|non.performing'),
    ('crar', r'\bcrar\b|capital|মূলধন'),
    ('net_profit', r'profit|মুনাফা|লাভ|লোকসান'),
    ('provision_shortfall', r'provision|প্রভিশন'),
]
LABELS = {'npl_ratio': ('খেলাপি ঋণ', 'Bad loans'), 'crar': ('মূলধন অনুপাত', 'Capital ratio'),
          'net_profit': ('নিট মুনাফা', 'Net profit'), 'provision_shortfall': ('প্রভিশন ঘাটতি', 'Provision shortfall')}


def provenance(source, fact_id):
    if not source: return None
    return {'fact_id': fact_id, 'source_url': source.url, 'source_title': source.title,
            'published_at': str(source.published_at) if source.published_at else None, 'page': source.page}


def detail_facts(text, institution_id, language, db):
    bn = language == 'bn'
    rows = []
    if re.search(r'rating|রেটিং', text, re.I):
        row = db.query(Rating).filter_by(institution_id=institution_id).order_by(Rating.rated_on.desc()).first()
        if row and row.source:
            rows.append({'text': f"{row.agency}: {row.long_term} ({row.rated_on})", **provenance(row.source, row.fact_id)})
        return rows
    news = bool(re.search(r'\bnews\b|খবর|সংবাদ', text, re.I))
    if news or re.search(r'fraud|incident|penalty|history|জালিয়াতি|জালিয়াতি|জরিমানা|ইতিহাস|সর্বশেষ ঘটনা', text, re.I):
        query = db.query(Event).filter_by(institution_id=institution_id)
        if news: query=query.filter_by(type='other')
        else: query=query.filter(Event.type!='other')
        for row in query.order_by(Event.event_date.desc()).all():
            if not row.sources: continue
            if not news and not row.official and len(row.sources)<2: continue
            label = ('খবরে প্রকাশিত, নিশ্চিত নয়। ' if bn else 'Reported, unconfirmed. ') if not row.official else ''
            rows.append({'text': label + (row.title_bn if bn else row.title_en) + f' ({row.event_date})',
                         'unconfirmed': not row.official, **provenance(row.sources[0], row.event_id)})
            if len(rows)==3:break
        return rows
    for metric, pattern in TOPICS:
        if not re.search(pattern, text, re.I): continue
        row = db.query(Fact).filter_by(institution_id=institution_id, metric=metric).order_by(Fact.period_end.desc()).first()
        if not row or not row.source: continue
        value = format(row.value * 100, '.2f').rstrip('0').rstrip('.') + '%' if row.unit == 'ratio' else format(row.value, 'f').split('.')[0] + (' টাকা' if bn else ' BDT')
        rows.append({'text': f"{LABELS[metric][0 if bn else 1]}: {value} ({row.period})", **provenance(row.source, row.fact_id)})
    return rows


def glossary_facts(text, language, db):
    query = normalize_alias(text)
    found = []
    for content in db.query(AppContent).filter(AppContent.lang == language, AppContent.status == 'live', AppContent.content_key.like('glossary:%')).order_by(AppContent.version.desc()):
        term = content.content_key.partition(':')[2]
        if normalize_alias(term) in query and content.content_key not in {row['fact_id'] for row in found}:
            found.append({'text': content.text, 'fact_id': content.content_key,
                          'source_title': 'ILMA glossary — FRD §21.2', 'source_url': None, 'published_at': None})
    return found[:3]
