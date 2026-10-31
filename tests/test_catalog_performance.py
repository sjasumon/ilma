"""Synthetic catalog parity and query budgets; no live source fixtures."""
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from ilma_api.db import Base, Fact, Institution, ServiceOffer, Source
from ilma_api.account_catalog import catalog
from ilma_api.bank_services import bank_view, demo_banks
from ilma_api.report_card import get_institution_report_card, status_inputs


@pytest.fixture
def db():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    today = date.today()
    with Session(engine) as session:
        session.add(Source(source_id='synthetic-source', url='https://example.example/report',
            title='Synthetic report', publisher='Synthetic', published_at=today,
            checked_by='synthetic', checked_on=today))
        for i, slug in enumerate(['bankasia', 'bracbank', 'citybank', 'ebl', 'mtb'], 1):
            session.add(Institution(id=i, slug=slug, name_bn='পরীক্ষা ব্যাংক',
                name_en='Synthetic '+str(i), type='bank', coverage='full', licensed=True,
                listed=True, islamic=False))
            if i != 4:
                for metric, value in [('crar', {1:.16, 2:.11, 3:.05, 5:.16}[i]), ('npl_ratio', .04)]:
                    session.add(Fact(fact_id=f'synthetic-{i}-{metric}', institution_id=i,
                        metric=metric, value=value, unit='ratio', period='2026',
                        period_end=today, source_id='synthetic-source', quote='Synthetic ratio',
                        checked_by='synthetic', checked_on=today, basis='standalone'))
            for kind, value in [('savings', 2), ('fdr', 11 if i == 5 else 8)]:
                session.add(ServiceOffer(offer_id=f'synthetic-{i}-{kind}', institution_id=i,
                    category='deposit', product='Synthetic '+kind, product_type=kind,
                    tenor_months=12, attribute='rate', value_text=str(value), value_num=value,
                    unit='pct_year', condition='Below 50 Lac', basis='conventional',
                    doc_date=today, stale=False, source_url='https://example.example/rates',
                    page=1, quote=f'Synthetic rate {value}%.', column_header='', variant='main',
                    hidden=False, hidden_reason='', checked_by='synthetic', checked_on=today))
        session.commit()
        yield session
    engine.dispose()


def test_bulk_status_matches_full_report_without_presentation(db):
    banks = demo_banks(db)
    inputs = status_inputs(db, banks)
    codes = {}
    for bank in banks:
        full = get_institution_report_card(db, bank.id)
        with patch('ilma_api.bank_screen.enrich', side_effect=AssertionError('list should not enrich')):
            light = get_institution_report_card(db, bank.id, status_only=True, inputs=inputs)
        assert light == {'status': full['status']}
        codes[bank.id] = light['status']['code']
    assert codes == {1:'strong', 2:'watch', 3:'high', 4:'no_data', 5:'watch'}


def test_account_queries_are_bounded_and_payload_matches_full_report_path(db):
    statements = []
    def count(*args):
        statements.append(1)
    event.listen(db.bind, 'before_cursor_execute', count)
    try:
        optimized = catalog(db)
    finally:
        event.remove(db.bind, 'before_cursor_execute', count)
    assert len(statements) <= 50
    def full_view(session, bank, **kwargs):
        card = get_institution_report_card(session, bank.id)
        return dict(id=bank.id, slug=bank.slug, name_bn=bank.name_bn, name_en=bank.name_en,
            status=card['status'], aliases=[row.alias for row in bank.aliases])
    with patch('ilma_api.bank_services.bank_view', side_effect=full_view):
        legacy = catalog(db)
    assert optimized == legacy


def test_targeted_savings_readouts_keep_full_source_binding(db):
    from ilma_api.deposit_catalog import catalog as deposits
    from ilma_api.deposit_readout import PLANS
    full = deposits(db, 'savings')
    targeted = deposits(db, 'savings', readout_plans=[p for p in PLANS if p[0]=='savings'])
    expected = {k:v for k,v in full['readouts'].items() if k.startswith('savings-')}
    assert targeted['readouts'] == expected
    assert targeted['catalog_banks'] == full['catalog_banks']
    assert any(r['product_type']=='fdr' for bank in targeted['catalog_banks'] for r in bank['rates'])
    row = db.get(ServiceOffer, 'synthetic-1-fdr')
    row.value_num = 9
    db.flush()
    updated = deposits(db, 'savings', readout_plans=[p for p in PLANS if p[0]=='savings'])
    assert updated['readouts']['savings-12-all']['source_sha256'] != expected['savings-12-all']['source_sha256']


def test_new_catalog_does_not_reuse_old_risk_in_same_session(db):
    assert next(b for b in catalog(db)['banks'] if b['id']==1)['status']['code']=='strong'
    db.get(Fact, 'synthetic-1-crar').value = .05
    db.flush()
    assert next(b for b in catalog(db)['banks'] if b['id']==1)['status']['code']=='high'
