"""Handwritten term expressions, never source-export fixtures."""
import pytest
from types import SimpleNamespace
from ilma_api.service_terms import parse_terms,matches_term

@pytest.mark.parametrize('text,low,high,options',[('1 to 6 Years',12,72,None),('3, 5, 7, 10 Years',36,120,[36,60,84,120]),('60M to 180M',60,180,None),('36M or 60M',36,60,[36,60]),('12 Months',12,12,[12])])
def test_ranges_and_discrete_choices(text,low,high,options):
    assert parse_terms('',text)==dict(tenor_min_months=low,tenor_max_months=high,tenor_options=options)

def test_discrete_three_or_five_year_offer_does_not_invent_four_years():
    row=SimpleNamespace(product='Synthetic DPS',condition='36M or 60M',tenor_months=None)
    assert matches_term(row,36) and matches_term(row,60) and not matches_term(row,48)
