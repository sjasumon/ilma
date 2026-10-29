"""Synthetic source-proof validation; annual reports are never test fixtures."""
import pytest
from ilma_api.profile_loader import validate

def row(**changes):
    return dict(field='branches',value='7',quote='7 branches',page='PDF 3',source_url='https://example.test/report.pdf',**changes)

def test_missing_quote_and_number_are_rejected():
    r=row();r['quote']=''
    with pytest.raises(ValueError):validate(r)
    r=row();r['value']='8'
    with pytest.raises(ValueError):validate(r)

def test_count_and_million_conversion_require_evidence():
    assert validate(row())['value']=='7'
    r=row();r.update(field='customers',value='2300000',quote='Customers 2.3 mn')
    assert validate(r)['value']=='2300000'
