"""Approved supplement integration and hostile-input regression checks."""
import csv
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import shutil

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from ilma_api.csv_loader import load as base
from ilma_api.incident_loader import load
from ilma_api.incident_export import inputs
from ilma_api.incidents import history, voice_facts
from ilma_api.db import BankIncident, Source, Fact, Rating, ServiceOffer, Institution
from ilma_api.report_card import get_institution_report_card
from ilma_api.bank_services import demo_banks
from ilma_api.voice_text import match_candidates

SEED=Path(__file__).resolve().parents[1]/'seed'

@pytest.fixture
def engine():
    engine=create_engine('sqlite://')
    base(SEED,engine)
    yield engine
    engine.dispose()


def test_sourced_high_cards_and_service_baseline(engine):
    result=load(SEED/'incidents',engine)
    assert result['statuses']=={'nbl':'high','islamibank':'high'}
    with Session(engine) as db:
        assert len(demo_banks(db))==9
        assert len(demo_banks(db,True))==11
        assert db.query(ServiceOffer).count()==610
        nbl=get_institution_report_card(db,36)
        islami=get_institution_report_card(db,26)
        assert nbl['status']['code']==islami['status']['code']=='high'
        assert all(r['source_url'] and r['quote'] for r in nbl['reasons']+islami['reasons'])
        assert db.scalar(select(Fact.value).where(Fact.institution_id==36,Fact.metric=='crar'))==__import__('decimal').Decimal('-.0548')
        assert db.scalar(select(Fact.value).where(Fact.institution_id==36,Fact.metric=='net_profit'))==-24298700000
        npl=db.query(Fact).filter_by(institution_id=26,metric='npl_ratio').one()
        assert npl.value==__import__('decimal').Decimal('.4966') and npl.basis=='solo_calculated'
        assert '94,322.59' in npl.quote and '189,951.52' in npl.quote
        assert [r['rule'] for r in islami['reasons']]==['H3','H4','W3']
        assert 'হিসাব করা' in islami['reasons'][1]['text_bn'] and 'অনিশ্চিত' in islami['reasons'][2]['text_bn']
        assert db.query(Rating).filter_by(institution_id=26).one().outlook=='developing'
        assert db.query(BankIncident).count()==19
        assert not db.query(BankIncident).filter(BankIncident.incident_id.contains('CITYBANK_EMBEZZLE_2026')).first()
        assert not db.query(BankIncident).filter_by(status_effect=True).first()
        for slug in ('bankasia','bracbank','citybank','dutchbangl','ebl','mtb','nccbank','primebank'):
            assert get_institution_report_card(db,slug)['status']['code']=='strong'
        assert get_institution_report_card(db,'sbacbank')['status']['code']=='no_data'


def test_reimport_review_and_qualified_history(engine):
    load(SEED/'incidents',engine)
    with Session(engine) as db:
        source=db.query(Source).filter(Source.source_id.like('v62-%')).first()
        sid=source.source_id;source.checked_by='Sumon';source.checked_on=date.today()
        incident=db.query(BankIncident).first();iid=incident.incident_id;incident.checked_by='Sumon';db.commit()
    load(SEED/'incidents',engine)
    with Session(engine) as db:
        assert db.get(Source,sid).checked_by=='Sumon'
        assert db.get(BankIncident,iid).checked_by=='Sumon'
        assert db.query(BankIncident).count()==19
        record=history(db,26)
        assert record['available'] and record['window'] is None and not record['complete_search']
        corrected=next(r for r in record['items'] if r['incident_id'].endswith('SCAM_2022'))
        assert corrected['status']=='reported' and not corrected['official']
        assert len(corrected['sources'])==2 and all(r['quote'] for r in corrected['sources'])
        assert corrected['older_history'] and not corrected['affects_status']
        assert all(r['status']=='reported' for r in corrected['changes'])
        assert not history(db,11)['available']  # absent records do not mean no cases
        for item in voice_facts(db,36,'en'):
            if item['unconfirmed']:assert 'Reported, unconfirmed.' in item['text']
        banks=[dict(id=b.id,slug=b.slug,name_bn=b.name_bn,name_en=b.name_en,type=b.type,coverage=b.coverage,
                    aliases=[a.alias for a in b.aliases]) for b in db.query(Institution)]
        for phrase,expected in [('NBL',36),('National Bank',36),('ন্যাশনাল ব্যাংক',36),('IBBL',26),('ইসলামী ব্যাংক',26)]:
            assert match_candidates(phrase,banks)[0]['id']==expected
        assert match_candidates('National',banks)[0]['confirm']


def test_unsafe_and_duplicate_zip_rejected(tmp_path):
    for filename in ('../incidents.csv','incidents.csv'):
        path=tmp_path/'bad.zip'
        with ZipFile(path,'w') as archive:
            archive.writestr(filename,'incident_id,status\nSYNTHETIC,reported\n')
            if filename=='incidents.csv':archive.writestr('nested/incidents.csv','incident_id,status\n')
        with pytest.raises(ValueError):inputs(path)


def test_unapproved_status_effect_rejected_without_mutation(engine,tmp_path):
    shutil.copytree(SEED/'incidents',tmp_path/'supplement')
    path=tmp_path/'supplement/bank_incident.csv'
    with path.open() as file:
        reader=csv.DictReader(file);fields=reader.fieldnames;rows=list(reader)
    rows[0]['status_effect']='true'
    with path.open('w') as file:
        writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    with pytest.raises(ValueError,match='unauthorized'):load(path.parent,engine)
    with Session(engine) as db:
        assert db.query(Institution).count()==9
        assert db.query(BankIncident).count()==0
