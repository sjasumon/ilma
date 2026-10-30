"""Handwritten presentation fixtures; no source export is copied here."""
import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from ilma_api.db import Base,Institution,BankProfile
from ilma_api.bank_screen import enrich,rating_meaning,publication_label,source_label
@pytest.fixture
def db():
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False});Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Institution(id=1,slug='synthetic',name_bn='পরীক্ষা ব্যাংক',name_en='Synthetic Bank',type='bank',coverage='full',licensed=True,listed=True,islamic=False));session.commit();yield session
    engine.dispose()
def card(code='no_data'):
    return {'institution':{'id':1,'slug':'synthetic','name_bn':'পরীক্ষা ব্যাংক','name_en':'Synthetic Bank'},'status':{'code':code},'reasons':[{'rule':'No data','text_bn':'সর্বশেষ তথ্য পাওয়া যায়নি।','source_url':None},{'rule':'P3','text_bn':'রেটিং A।','source_url':'https://example.example/rating','source_title':'Synthetic rating 2026'}], 'ratings':[{'agency':'CRISL','long_term':'A'}],'figures':[],'incident_count':0,'insurance':{'covered':False}}
def test_not_rated_has_only_sourced_reason_and_no_invented_profile(db):
    result=enrich(db,card())
    assert result['status']['label_bn']=='মূল্যায়ন করা হয়নি'
    assert len(result['reasons'])==1 and result['ratings'][0]['meaning_bn']=='উঁচু'
    assert result['founded_year'] is None and result['award'] is None
    assert set(result['section_counts'].values())=={0,1}
    assert 'পাওয়া যায়নি' not in result['readout']['text']
    assert result['readout']['audio_url'] is None
def test_sourced_profile_and_negative_ratio_are_not_rounded(db):
    db.add(BankProfile(fact_id='synthetic-year',bank_id=1,field='founded_year',value='1999',as_of=date(2026,1,1),source_url='https://example.example/report',page='1',quote='Founded 1999'));db.flush()
    data=card('high');data['reasons']=[{'rule':'H3','text_bn':'মূলধন অনুপাত -৫.৪৮%।','source_url':'https://example.example/report','source_title':'Annual Report 2025'}]
    result=enrich(db,data);assert result['founded_year']=='1999'
    assert 'মাইনাস পাঁচ দশমিক চার আট শতাংশ' in result['readout']['text']
    assert result['readout']['text'].startswith('প্রকাশিত তথ্য অনুযায়ী ঝুঁকি বেশি')
    assert db.get(BankProfile,'synthetic-year') is not None
@pytest.mark.parametrize('grade,meaning',[('AAA','সর্বোচ্চ গ্রেড'),('AA-','খুব উঁচু'),('A+','উঁচু'),('BBB-','মাঝারি'),('BB','নিচু')])
def test_agency_rating_meanings(grade,meaning):assert rating_meaning('CRISL',grade)['meaning_bn']==meaning
def test_publication_labels_keep_original_title_and_year():
    row=SimpleNamespace(topic='board_meeting',title='Election of Chairman',kind='announcement',report_year=None)
    assert publication_label(row)['type_label_bn']=='চেয়ারম্যান নির্বাচন'
    row=SimpleNamespace(topic='financials',title='First Quarter 2026 (Unaudited)',kind='report',report_year=2026)
    assert publication_label(row)['type_label_bn']=='প্রথম প্রান্তিক ২০২৬ (অনিরীক্ষিত)'
    assert source_label('Annual Report 2025',date(2026,5,1))=='বার্ষিক প্রতিবেদন ২০২৫'
def test_report_readout_never_generates_runtime_speech(db):
    from ilma_api.voice_pipeline import readout
    with patch('ilma_api.voice_pipeline.readout_result',return_value={'text':'legacy'}),patch('ilma_api.voice_pipeline.get_institution_report_card',return_value={'readout':{'text':'শুধু সংরক্ষিত বর্ণনা।','audio_url':None}}),patch('ilma_api.audio_cache.register_speech',new=AsyncMock()) as tts,patch('httpx.AsyncClient.post',new=AsyncMock()) as provider:
        result=asyncio.run(readout('report_card',1,'bn',db))
    assert result['text']=='শুধু সংরক্ষিত বর্ণনা।' and result['audio_url'] is None
    tts.assert_not_awaited();provider.assert_not_awaited()

def test_awards_require_low_risk_and_confirmed_nonpaid_evidence():
    from ilma_api.bank_screen import eligible_award
    rows=[dict(bank_slug='synthetic',title_bn='পরীক্ষা স্বীকৃতি',title_en='Synthetic award',source_url='https://example.example/award',quote='Synthetic confirmation',year='2026',awarder_confirmed='true',likely_paid='false')]
    assert eligible_award('synthetic','strong',rows)
    assert eligible_award('synthetic','high',rows) is None
    assert eligible_award('synthetic','no_data',rows) is None
    rows[0]['likely_paid']='true';assert eligible_award('synthetic','strong',rows) is None
    rows[0]['likely_paid']='false';rows[0]['awarder_confirmed']='false';assert eligible_award('synthetic','strong',rows) is None

def test_saved_bank_script_requires_matching_frozen_facts(db,tmp_path,monkeypatch):
    import hashlib,json
    from ilma_api import bank_screen
    seed=tmp_path/'seed';seed.mkdir()
    (seed/'rating_scale_bn.csv').write_text('agency,grade,meaning_bn,meaning_en\nCRISL,A,উঁচু,High\n')
    (seed/'bank_awards.csv').write_text('bank_slug,title_bn,title_en,source_url,quote,year,awarder_confirmed,likely_paid\n')
    monkeypatch.setattr(bank_screen,'ROOT',tmp_path)
    initial=enrich(db,card());directory=tmp_path/'static/audio/bank/bn';directory.mkdir(parents=True)
    audio=b'synthetic-bank-audio';(directory/'synthetic.mp3').write_bytes(audio)
    text=initial['readout']['text']
    entry=dict(file='bn/synthetic.mp3',text=text,text_sha256=hashlib.sha256(text.encode()).hexdigest(),audio_sha256=hashlib.sha256(audio).hexdigest(),source_sha256=initial['readout']['source_sha256'],approved_exact_text=True,reviewed=True)
    (directory.parent/'manifest.json').write_text(json.dumps({'clips':{'synthetic':entry}}))
    matched=enrich(db,card())['readout'];assert matched['text']==text and matched['audio_url']
    changed=card();changed['ratings'][0]['long_term']='AA'
    stale=enrich(db,changed)['readout'];assert stale['audio_url'] is None and stale['text']!=text

    revised=card();revised['reasons'][1]['source_url']='https://example.example/revised-source'
    assert enrich(db,revised)['readout']['audio_url'] is None

def test_approved_original_key_and_underscore_filename_with_profile_guard(db,tmp_path,monkeypatch):
    import hashlib,json
    from ilma_api import bank_screen
    seed=tmp_path/'seed';seed.mkdir()
    (seed/'rating_scale_bn.csv').write_text('agency,grade,meaning_bn,meaning_en\nCRISL,A,উঁচু,High\n')
    (seed/'bank_awards.csv').write_text('bank_slug,title_bn,title_en,source_url,quote,year,awarder_confirmed,likely_paid\n')
    monkeypatch.setattr(bank_screen,'ROOT',tmp_path)
    initial=enrich(db,card());audio=b'synthetic-bytes';directory=tmp_path/'static/audio/bank/bn';directory.mkdir(parents=True);(directory/'sample_bank.mp3').write_bytes(audio)
    entry=dict(key='bank:bn:sample_bank',bank_slug='synthetic',file='bn/sample_bank.mp3',text='পরীক্ষার অনুমোদিত পাঠ।',text_sha256=hashlib.sha256('পরীক্ষার অনুমোদিত পাঠ।'.encode()).hexdigest(),audio_sha256=hashlib.sha256(audio).hexdigest(),source_sha256=initial['readout']['source_sha256'],approved_exact_text=True,reviewed=True)
    (directory.parent/'manifest.json').write_text(json.dumps({'clips':{'bank:bn:sample_bank':entry}}))
    assert '/sample_bank.mp3?v=' in enrich(db,card())['readout']['audio_url']
    import csv
    with (seed/'bank_profile_facts.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,['bank','fact_bn','value','source_url','as_of','source_note']);writer.writeheader();writer.writerow(dict(bank='synthetic',fact_bn='পরীক্ষার পরিচিতি।',value='{}',source_url='https://example.example/profile',as_of='',source_note='Synthetic evidence'))
    updated=enrich(db,card());assert updated['profile_facts'][0]['fact_bn']=='পরীক্ষার পরিচিতি।' and updated['readout']['audio_url'] is None
