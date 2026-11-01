"""Handwritten review sections prevent reference/proposal selection mistakes."""
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('reviewed_answer_master',Path(__file__).resolve().parents[1]/'scripts/reviewed_answer_master.py');master=importlib.util.module_from_spec(spec);spec.loader.exec_module(master)
DOCUMENT='''## Q1. Synthetic question

**Current/reference full answer — Bangla**

পরীক্ষার পূর্ণ উত্তর। আরও জানতে চান?

**Proposed full spoken answer — Bangla**

ছোট প্রস্তাব।

**Current/reference full answer — English**

A synthetic answer.
'''

def test_reference_is_kept_verbatim_with_its_question():
    assert master.reference_bangla(DOCUMENT,1)=={1:'পরীক্ষার পূর্ণ উত্তর। আরও জানতে চান?'}

@pytest.mark.parametrize('document',[DOCUMENT.replace('Current/reference full answer — Bangla','Other section'),DOCUMENT+DOCUMENT,DOCUMENT.replace('পরীক্ষার পূর্ণ উত্তর। আরও জানতে চান?','')])
def test_invalid_reference_never_falls_back_to_proposed(document):
    with pytest.raises(ValueError):master.reference_bangla(document,1)

def test_only_explicit_legacy_closing_exception_is_removed():
    document=DOCUMENT.replace('আরও জানতে চান?',master.LEGACY_CLOSING)
    assert master.reference_bangla(document,1)[1]=='পরীক্ষার পূর্ণ উত্তর।'
